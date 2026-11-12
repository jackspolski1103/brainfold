from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from oif import OIFError
from oif.brain import Brain

EXAMPLE = Path(__file__).parent.parent / "examples" / "brain"
ALICE, BOB, REVIEWER, CARLA = (
    f"{name}@atlas.test" for name in ("alice", "bob", "reviewer", "carla")
)


@pytest.fixture
def groups() -> dict[str, list[str]]:
    return {"costs": [ALICE, REVIEWER], "contracts": [BOB, REVIEWER]}


@pytest.fixture
def brain(tmp_path: Path, groups: dict[str, list[str]]) -> Brain:
    shutil.copytree(EXAMPLE, tmp_path / "brain")
    return Brain(tmp_path / "brain", lambda: groups)


def paths(listing: dict) -> list[str]:
    return [entry["path"] for entry in listing["entries"]]


def denied(call, *args) -> str:
    with pytest.raises(OIFError) as error:
        call(*args)
    return error.value.code


def test_listing_guides_and_hides_what_is_not_granted(brain: Brain) -> None:
    root = brain.list(ALICE, "/")
    assert root["start_here"] and root["description"]
    assert {e["path"]: e.get("description") for e in root["entries"]}["/skills"]
    assert "read" not in root
    assert paths(brain.list(ALICE, "/proyectos")) == ["/proyectos/costos"]
    assert paths(brain.list(BOB, "/proyectos")) == ["/proyectos/contratos"]
    assert paths(brain.list(BOB, "/personas")) == []
    assert not any(".oif" in path for path in paths(root))


def test_skills_are_discovered_only_where_readable(brain: Brain) -> None:
    assert brain.skills(ALICE)["skills"] == [
        {
            "path": "/skills/analizar-costos/SKILL.md",
            "name": "analizar-costos",
            "description": "Analizar costos de un proyecto sin presentar totales a partir de "
            "muestras truncadas.",
        }
    ]
    assert brain.skills(BOB)["skills"] == []


def test_denials_are_indistinguishable_from_absence(brain: Brain) -> None:
    for who, call, path in (
        (BOB, brain.read, "/personas/alice/preferencias.md"),
        (BOB, brain.read, "/personas/alice/no-existe.md"),
        (REVIEWER, brain.read, "/personas/alice/preferencias.md"),
        (CARLA, brain.list, "/"),
        (ALICE, brain.read, "/.oif.toml"),
        (ALICE, brain.read, "/comun/../.oif.toml"),
        (ALICE, brain.list, "/.git"),
        (ALICE, brain.read, "comun/convenciones.md"),
        (ALICE, brain.read, "/comun//convenciones.md"),
        (ALICE, brain.read, "/comun/%2e%2e/.oif.toml"),
        (ALICE, brain.read, "/comun\\convenciones.md"),
    ):
        assert denied(call, who, path) == "ruta_no_disponible"


def test_symlinks_and_broken_metadata_fail_closed(brain: Brain) -> None:
    (brain.root / "comun" / "fuga.md").symlink_to(
        brain.root / "personas" / "alice" / "preferencias.md"
    )
    assert "/comun/fuga.md" not in paths(brain.list(BOB, "/comun"))
    assert denied(brain.read, BOB, "/comun/fuga.md") == "ruta_no_disponible"
    (brain.root / "comun" / ".oif.toml").write_text("read = 'alice'")
    assert denied(brain.read, ALICE, "/comun/convenciones.md") == "ruta_no_disponible"


def test_write_needs_its_own_grant_and_revocation_applies_at_once(
    brain: Brain, groups: dict[str, list[str]]
) -> None:
    assert brain.list(ALICE, "/proyectos/costos")["can_write"]
    brain.write(ALICE, "/proyectos/costos/notas/aprendizaje.md", "v1")
    assert brain.read(REVIEWER, "/proyectos/costos/notas/aprendizaje.md")["content"] == "v1"
    assert brain.search(REVIEWER, "V1")["hits"][0]["path"].endswith("aprendizaje.md")
    assert brain.search(BOB, "v1")["hits"] == []
    # Readable but not writable, unreadable, metadata and folders.
    assert denied(brain.write, ALICE, "/comun/convenciones.md", "x") == "sin_permiso_escritura"
    assert denied(brain.write, BOB, "/proyectos/costos/x.md", "x") == "ruta_no_disponible"
    assert denied(brain.write, ALICE, "/proyectos/costos/.oif.toml", "x") == "ruta_no_disponible"
    assert denied(brain.write, ALICE, "/proyectos/costos", "x") == "ruta_no_disponible"
    assert denied(brain.write, ALICE, "/proyectos/costos/g.md", "x" * 70_000) == (
        "archivo_demasiado_grande"
    )
    groups["costs"].remove(ALICE)
    assert denied(brain.read, ALICE, "/proyectos/costos/proceso.md") == "ruta_no_disponible"


def test_administrators_manage_grants_without_reading_content(brain: Brain) -> None:
    managed = brain.list(CARLA, "/proyectos", manage=True)
    assert {e["path"]: e["read"] for e in managed["entries"]} == {
        "/proyectos/contratos": ["@contracts"],
        "/proyectos/costos": ["@costs"],
    }
    assert denied(brain.read, CARLA, "/proyectos/costos/proceso.md") == "ruta_no_disponible"
    brain.set_meta(CARLA, "/proyectos/costos", 'Costos "2026"', [], ["@costs", BOB], None)
    assert brain.read(BOB, "/proyectos/costos/proceso.md")["content"]
    assert not brain.list(ALICE, "/proyectos/costos")["can_write"]  # write no longer declared
    assert brain.list(ALICE, "/proyectos/costos")["description"] == 'Costos "2026"'
    for bad in (["no es un grant"], ["@Grupo Inválido"]):
        assert (
            denied(brain.set_meta, CARLA, "/proyectos/costos", "", [], bad, None)
            == "metadata_invalida"
        )
    assert denied(brain.set_meta, CARLA, "/comun", "", ["../x"], None, None) == "metadata_invalida"


def test_writes_are_committed_when_the_brain_is_a_git_repository(brain: Brain) -> None:
    subprocess.run(["git", "init", "-q", str(brain.root)], check=True)
    assert brain.write(ALICE, "/personas/alice/nota.md", "hola")["versioned"]
    log = subprocess.run(
        ["git", "-C", str(brain.root), "log", "--format=%ae %s"], capture_output=True, text=True
    )
    assert log.stdout.strip() == f"{ALICE} {ALICE}: personas/alice/nota.md"
