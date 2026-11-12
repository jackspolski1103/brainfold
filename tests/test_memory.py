from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

from oif.domain import MemoryNode, OIFError, Principal
from oif.memory import MAX_FILE_BYTES, PermissionedMemory


def principal(
    name: str = "alice", projects: frozenset[str] = frozenset({"costs"}), **kwargs: object
) -> Principal:
    return Principal(id=name, organization_id="example", project_ids=projects, **kwargs)


def node(path: str, kind: str = "file", **kwargs: object) -> MemoryNode:
    values: dict[str, object] = {
        "organization_id": "example",
        "path": path,
        "kind": kind,
        "status": "published",
    }
    values.update(kwargs)
    return MemoryNode(**values)


def repository(*extra_nodes: MemoryNode) -> PermissionedMemory:
    return PermissionedMemory(
        [
            node("/", "directory", allowed_projects=frozenset({"costs", "contracts"})),
            node("/shared", "directory"),
            node("/shared/data.md", content="Synthetic shared conventions"),
            node("/costs", "directory", allowed_projects=frozenset({"costs"})),
            node("/costs/private.md", content="Synthetic costs-only convention"),
            *extra_nodes,
        ]
    )


async def test_lists_only_authorized_metadata_and_reads_content() -> None:
    memory = repository()
    assert await memory.list_directory("example", "/shared", [principal()]) == [
        {"path": "/shared/data.md", "kind": "file", "version": 1}
    ]
    assert await memory.read_file("example", "/shared/data.md", [principal()]) == {
        "path": "/shared/data.md",
        "version": 1,
        "content": "Synthetic shared conventions",
    }
    listing = await memory.list_directory(
        "example", "/", [principal("bob", frozenset({"contracts"}))]
    )
    assert listing == [{"path": "/shared", "kind": "directory", "version": 1}]


async def test_ancestor_permissions_intersect_and_child_cannot_widen_them() -> None:
    memory = repository(
        node("/costs/widened.md", allowed_projects=frozenset({"contracts"}), content="hidden"),
        node("/shared/alice.md", allowed_principals=frozenset({"alice"}), content="restricted"),
    )
    assert (await memory.read_file("example", "/costs/private.md", [principal()]))["content"]
    for actor, path in [
        (principal("bob", frozenset({"contracts"})), "/costs/widened.md"),
        (principal(), "/costs/widened.md"),
        (principal("bob"), "/shared/alice.md"),
    ]:
        with pytest.raises(OIFError, match="La ruta no está disponible") as caught:
            await memory.read_file("example", path, [actor])
        assert caught.value.code == "ruta_no_disponible"


async def test_both_acl_dimensions_must_allow_every_principal() -> None:
    memory = repository(
        node(
            "/shared/restricted.md",
            content="restricted",
            allowed_projects=frozenset({"costs"}),
            allowed_principals=frozenset({"alice", "bob"}),
        )
    )
    assert await memory.read_file(
        "example", "/shared/restricted.md", [principal(), principal("bob")]
    )
    for readers in [
        [principal(), principal("bob", frozenset({"contracts"}))],
        [principal(), principal("eve")],
        [],
    ]:
        with pytest.raises(OIFError) as caught:
            await memory.read_file("example", "/shared/restricted.md", readers)
        assert caught.value.code == "ruta_no_disponible"


async def test_organization_and_active_status_are_checked_for_requester_and_audience() -> None:
    memory = repository()
    other = Principal(id="mallory", organization_id="other", project_ids=frozenset({"costs"}))
    inactive = principal("inactive", active=False)
    for readers in [[other], [principal(), other], [inactive], [principal(), inactive]]:
        with pytest.raises(OIFError) as caught:
            await memory.read_file("example", "/shared/data.md", readers)
        assert caught.value.code == "ruta_no_disponible"
    with pytest.raises(OIFError):
        await memory.read_file("other", "/shared/data.md", [principal()])


async def test_same_path_is_isolated_per_organization() -> None:
    memory = repository(
        node("/", "directory", organization_id="other", allowed_principals=frozenset({"alice"})),
        node("/shared", "directory", organization_id="other"),
        node("/shared/data.md", organization_id="other", content="Other organization synthetic"),
    )
    ours = await memory.read_file("example", "/shared/data.md", [principal()])
    actor = Principal(id="alice", organization_id="other", project_ids=frozenset())
    theirs = await memory.read_file("other", "/shared/data.md", [actor])
    assert ours["content"] != theirs["content"]


@pytest.mark.parametrize("status", ["draft", "revoked"])
async def test_non_published_files_and_subtrees_are_hidden(status: str) -> None:
    memory = repository(
        node("/shared/hidden.md", content="hidden", status=status),
        node("/hidden", "directory", status=status),
        node("/hidden/public.md", content="published file behind a hidden ancestor"),
    )
    shared = await memory.list_directory("example", "/shared", [principal()])
    assert shared == [{"path": "/shared/data.md", "kind": "file", "version": 1}]
    assert all(
        item["path"] != "/hidden"
        for item in await memory.list_directory("example", "/", [principal()])
    )
    for path in ["/shared/hidden.md", "/hidden/public.md"]:
        with pytest.raises(OIFError) as caught:
            await memory.read_file("example", path, [principal()])
        assert caught.value.code == "ruta_no_disponible"


async def test_root_without_grant_or_with_empty_acl_denies_descendant_grants() -> None:
    for acl in [{}, {"allowed_projects": frozenset()}, {"allowed_principals": frozenset()}]:
        memory = PermissionedMemory(
            [
                node("/", "directory", **acl),
                node("/file.md", allowed_principals=frozenset({"alice"}), content="hidden"),
            ]
        )
        with pytest.raises(OIFError):
            await memory.read_file("example", "/file.md", [principal()])
        with pytest.raises(OIFError):
            await memory.list_directory("example", "/", [principal()])


async def test_missing_ancestors_and_files_used_as_directories_do_not_grant_access() -> None:
    memory = repository(
        node("/missing/file.md", content="orphaned"),
        node("/shared/data.md/child.md", content="not a real directory"),
    )
    for path in ["/missing/file.md", "/shared/data.md/child.md"]:
        with pytest.raises(OIFError):
            await memory.read_file("example", path, [principal()])


@pytest.mark.parametrize(
    "path",
    [
        "shared/data.md",
        "//shared/data.md",
        "/shared/../costs/private.md",
        "/./shared/data.md",
        "/shared//data.md",
        "/shared/",
        "/shared\\data.md",
        "/shared/%2e%2e/data.md",
        "/shared/%252e%252e/data.md",
        "/shared/%2fdata.md",
        "/shared/\x00data.md",
        "/shared/\ndata.md",
    ],
)
async def test_noncanonical_paths_are_rejected_without_normalization(path: str) -> None:
    with pytest.raises(OIFError) as caught:
        await repository().read_file("example", path, [principal()])
    assert (caught.value.code, caught.value.message) == (
        "ruta_no_disponible",
        "La ruta no está disponible.",
    )


async def test_missing_denied_and_wrong_kind_have_identical_errors() -> None:
    memory = repository()
    errors = []
    for path in ["/absent.md", "/costs/private.md", "/shared"]:
        with pytest.raises(OIFError) as caught:
            await memory.read_file("example", path, [principal("bob", frozenset({"contracts"}))])
        errors.append(caught.value.info())
    assert errors[0] == errors[1] == errors[2]
    with pytest.raises(OIFError) as caught:
        await memory.list_directory("example", "/shared/data.md", [principal()])
    assert caught.value.info() == errors[0]


async def test_revocation_takes_effect_on_next_operation_and_versions_are_current() -> None:
    memory = repository()
    assert memory.revision == 1
    memory.replace_node(node("/shared/data.md", version=2, content="Updated synthetic convention"))
    assert memory.revision == 2
    assert (await memory.read_file("example", "/shared/data.md", [principal()]))["version"] == 2
    memory.replace_node(node("/shared", "directory", status="revoked", version=2))
    assert memory.revision == 3
    with pytest.raises(OIFError):
        await memory.read_file("example", "/shared/data.md", [principal()])
    assert (
        await memory.list_directory("example", "/", [principal("bob", frozenset({"contracts"}))])
        == []
    )


async def test_trusted_concurrent_replacement_publishes_complete_snapshots() -> None:
    memory = repository()
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(
                memory.replace_node,
                node("/shared/data.md", version=version, content=f"synthetic version {version}"),
            )
            for version in range(2, 20)
        ]
        for future in futures:
            future.result()
    data = await memory.read_file("example", "/shared/data.md", [principal()])
    assert data["content"] == f"synthetic version {data['version']}"
    assert memory.revision == 19


def test_configuration_bounds_reject_invalid_entries_without_touching_filesystem() -> None:
    with pytest.raises(OIFError) as caught:
        repository(node("/too-large.md", content="x" * (MAX_FILE_BYTES + 1)))
    assert caught.value.code == "configuracion_invalida"
    with pytest.raises(OIFError):
        repository(node("/shared/../bad.md"))
    with pytest.raises(OIFError):
        repository(node("/shared/data.md"))
