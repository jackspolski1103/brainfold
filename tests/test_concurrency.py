"""Several people and agents touching the same things at the same instant.

Every test lines its callers up behind a barrier and releases them together against a
real server. Whatever the interleaving, exactly one conflicting change may win, nothing
may be lost silently, and git must hold every change that was acknowledged.
"""
# ruff: noqa: B023 (each round's callers run and finish inside its own loop iteration)

from __future__ import annotations

import hashlib
import random
import threading
import time
from collections import Counter
from collections.abc import Iterator

import pytest
from team import ADMIN, Person, Team, serving, together
from test_multiuser import assert_sound, git

PEOPLE = 10


@pytest.fixture(scope="module")
def team(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Team]:
    base = tmp_path_factory.mktemp("crowd")
    with serving(base / "brain", base / "brainfold.db") as team:
        team.access("/", ["*"], [ADMIN])
        team.crowd = [team.join(f"user{number}@atlas.test") for number in range(PEOPLE)]
        team.group("writers", *team.crowd)
        team.admin.tool("create_folder", path="/shared", description="Where everyone writes.")
        team.access("/shared", ["@writers"], ["@writers"], "Where everyone writes.")
        yield team
        assert_sound(team)


@pytest.fixture
def crowd(team: Team) -> list[Person]:
    return team.crowd


def outcomes(answers: list[tuple[str, object]]) -> Counter[str]:
    return Counter(answer[0] for answer in answers)


def text(team: Team, path: str) -> str:
    return (team.root / path[1:]).read_text("utf-8")


def commits(team: Team, path: str) -> int:
    return len(git(team, "log", "--format=%H", "--", path[1:]).split())


def test_everyone_creating_the_same_file_at_once_one_wins(team: Team, crowd: list[Person]) -> None:
    path = "/shared/created.md"
    answers = together(
        *(lambda p=person: p.tool("write", path=path, content=f"by {p.email}") for person in crowd)
    )
    assert outcomes(answers) == {"ok": 1, "already_exists": PEOPLE - 1}
    winner = crowd[[answer[0] for answer in answers].index("ok")]
    assert text(team, path) == f"by {winner.email}"
    # Every loser was told the version to read, and it is the winner's.
    version = hashlib.sha256(text(team, path).encode()).hexdigest()
    assert all(version in answer[1] for answer in answers if answer[0] != "ok")
    history = winner.tool("history", path=path)[1]["revisions"]
    assert [(r["author"], r["change"]) for r in history] == [(winner.email, "write")]
    assert commits(team, path) == 1


def test_everyone_replacing_the_same_version_at_once_one_wins(
    team: Team, crowd: list[Person]
) -> None:
    path = "/shared/replaced.md"
    version = crowd[0].tool("write", path=path, content="start")[1]["version"]
    for round_number in range(3):
        answers = together(
            *(
                lambda p=person: p.tool(
                    "write",
                    path=path,
                    content=f"round {round_number} by {p.email}",
                    version=version,
                )
                for person in crowd
            )
        )
        assert outcomes(answers) == {"ok": 1, "conflict": PEOPLE - 1}, answers
        winner = crowd[[answer[0] for answer in answers].index("ok")]
        assert text(team, path) == f"round {round_number} by {winner.email}"
        version = next(answer[1]["version"] for answer in answers if answer[0] == "ok")
        assert all(version in answer[1] for answer in answers if answer[0] != "ok")
    history = crowd[0].tool("history", path=path)[1]["revisions"]
    assert [r["change"] for r in history] == ["write"] * 4
    assert commits(team, path) == 4


def test_no_appended_line_is_ever_lost(team: Team, crowd: list[Person]) -> None:
    path = "/shared/LEARNINGS.md"
    rounds = 4
    for round_number in range(rounds):
        answers = together(
            *(
                lambda p=person: p.tool(
                    "append", path=path, content=f"note {round_number} of {p.email}"
                )
                for person in crowd
            )
        )
        assert outcomes(answers) == {"ok": PEOPLE}, answers
    lines = [line for line in text(team, path).splitlines() if line.startswith("note ")]
    assert Counter(lines) == Counter(f"note {r} of {p.email}" for r in range(rounds) for p in crowd)
    learned = crowd[0].tool("list_learnings", limit=200)[1]["learnings"]
    assert Counter((entry["author"], entry["text"]) for entry in learned) == Counter(
        (p.email, f"note {r} of {p.email}") for r in range(rounds) for p in crowd
    )
    assert commits(team, path) == rounds * PEOPLE


def test_edits_of_different_parts_all_land_and_edits_of_the_same_part_do_not_stack(
    team: Team, crowd: list[Person]
) -> None:
    path = "/shared/table.md"
    crowd[0].tool("write", path=path, content="".join(f"row{n}: empty\n" for n in range(PEOPLE)))
    answers = together(
        *(
            lambda p=person, n=number: p.tool(
                "edit", path=path, old=f"row{n}: empty", new=f"row{n}: {p.email}"
            )
            for number, person in enumerate(crowd)
        )
    )
    assert outcomes(answers) == {"ok": PEOPLE}
    assert text(team, path) == "".join(f"row{n}: {p.email}\n" for n, p in enumerate(crowd))
    # Everyone now fights for the same line: the first takes it, the rest find it gone.
    target = f"row0: {crowd[0].email}"
    answers = together(
        *(
            lambda p=person: p.tool("edit", path=path, old=target, new=f"row0: taken by {p.email}")
            for person in crowd
        )
    )
    assert outcomes(answers) == {"ok": 1, "invalid_edit": PEOPLE - 1}
    winner = crowd[[answer[0] for answer in answers].index("ok")]
    assert text(team, path).splitlines()[0] == f"row0: taken by {winner.email}"


def test_panel_and_harness_uploads_of_the_same_file_at_once_one_wins(
    team: Team, crowd: list[Person]
) -> None:
    path = "/shared/sheet.xlsx"
    body = {person.email: bytes([number]) * 200_000 for number, person in enumerate(crowd)}

    def send(person: Person, number: int, version: str | None = None) -> tuple[int, bytes]:
        if number % 2:
            return person.upload(path, body[person.email], version).status_code, body[person.email]
        headers = {"If-Match": f'"{version}"'} if version else {}
        response = person.agent.put(f"/files{path}", content=body[person.email], headers=headers)
        return response.status_code, body[person.email]

    answers = together(
        *(lambda p=person, n=number: send(p, n) for number, person in enumerate(crowd))
    )
    assert Counter(status for status, _ in answers) == {200: 1, 409: PEOPLE - 1}
    stored = next(data for status, data in answers if status == 200)
    assert (team.root / path[1:]).read_bytes() == stored
    # Replacing needs the version; with the same one for all, one replaces.
    version = hashlib.sha256(stored).hexdigest()
    answers = together(
        *(lambda p=person, n=number: send(p, n, version) for number, person in enumerate(crowd))
    )
    assert Counter(status for status, _ in answers) == {200: 1, 409: PEOPLE - 1}
    stored = next(data for status, data in answers if status == 200)
    downloaded = crowd[0].download(path)
    assert downloaded.content == stored == (team.root / path[1:]).read_bytes()
    assert downloaded.headers["etag"] == f'"{hashlib.sha256(stored).hexdigest()}"'
    assert commits(team, path) == 2


def test_delete_move_and_write_of_the_same_version_at_once_one_wins(
    team: Team, crowd: list[Person]
) -> None:
    for round_number in range(4):
        path = f"/shared/contested-{round_number}.md"
        version = crowd[0].tool("write", path=path, content="original")[1]["version"]
        calls = []
        for number, person in enumerate(crowd):
            moved = f"/shared/moved-{round_number}-{number}.md"
            calls.append(
                [
                    lambda p=person: p.tool("delete", path=path, version=version),
                    lambda p=person, d=moved: p.tool(
                        "move", source=path, destination=d, version=version
                    ),
                    lambda p=person: p.tool(
                        "write", path=path, content=f"rewritten by {p.email}", version=version
                    ),
                ][number % 3]
            )
        answers = together(*calls)
        assert outcomes(answers)["ok"] == 1, answers
        assert set(outcomes(answers)) <= {"ok", "conflict"}, answers
        winner = [answer[0] for answer in answers].index("ok")
        there = (team.root / path[1:]).exists()
        moved = sorted(p.name for p in (team.root / "shared").glob(f"moved-{round_number}-*"))
        if winner % 3 == 0:  # deleted
            assert not there and not moved
        elif winner % 3 == 1:  # moved: in exactly one new place, content intact
            assert not there and moved == [f"moved-{round_number}-{winner}.md"]
            assert text(team, f"/shared/{moved[0]}") == "original"
        else:
            assert there and not moved
            assert text(team, path) == f"rewritten by {crowd[winner].email}"


def test_two_people_moving_different_files_onto_the_same_name_at_once(
    team: Team, crowd: list[Person]
) -> None:
    versions = [
        person.tool("write", path=f"/shared/draft-{number}.md", content=f"draft {number}")[1][
            "version"
        ]
        for number, person in enumerate(crowd)
    ]
    answers = together(
        *(
            lambda p=person, n=number: p.tool(
                "move",
                source=f"/shared/draft-{n}.md",
                destination="/shared/final.md",
                version=versions[n],
            )
            for number, person in enumerate(crowd)
        )
    )
    assert outcomes(answers) == {"ok": 1, "already_exists": PEOPLE - 1}
    winner = [answer[0] for answer in answers].index("ok")
    assert text(team, "/shared/final.md") == f"draft {winner}"
    left = sorted(p.name for p in (team.root / "shared").glob("draft-*"))
    assert left == sorted(f"draft-{n}.md" for n in range(PEOPLE) if n != winner)


def test_folders_created_described_and_filled_at_once(team: Team, crowd: list[Person]) -> None:
    answers = together(
        *(
            lambda p=person: p.tool("create_folder", path="/shared/room", description=p.email)
            for person in crowd
        )
    )
    assert outcomes(answers) == {"ok": 1, "already_exists": PEOPLE - 1}
    # Everyone describes a different file of the same folder: one metadata file, no loss.
    for number, person in enumerate(crowd):
        person.tool("write", path=f"/shared/room/file-{number}.md", content="x")
    answers = together(
        *(
            lambda p=person, n=number: p.tool(
                "describe_file", path=f"/shared/room/file-{n}.md", description=f"about {n}"
            )
            for number, person in enumerate(crowd)
        )
    )
    assert outcomes(answers) == {"ok": PEOPLE}
    listing = crowd[0].tool("list", path="/shared/room")[1]["entries"]
    assert {e["path"]: e.get("description") for e in listing} == {
        f"/shared/room/file-{n}.md": f"about {n}" for n in range(PEOPLE)
    }
    # While people write into a deep new path, each new folder is created exactly once.
    answers = together(
        *(
            lambda p=person, n=number: p.tool("write", path=f"/shared/a/b/c/{n}.md", content="x")
            for number, person in enumerate(crowd)
        )
    )
    assert outcomes(answers) == {"ok": PEOPLE}
    assert len(list((team.root / "shared/a/b/c").iterdir())) == PEOPLE


def test_everyone_works_in_their_own_folder_at_once_and_nothing_crosses_over(
    team: Team, crowd: list[Person]
) -> None:
    homes = [person.tool("list")[1]["home"] for person in crowd]
    assert len(set(homes)) == PEOPLE

    def work(person: Person, home: str, target: str) -> list[str]:
        seen = [
            person.tool("write", path=f"{home}/secret.md", content=f"private of {person.email}")[0],
            person.tool("read", path=f"{target}/secret.md")[0],
            person.tool("list", path=target)[0],
            person.tool("write", path=f"{target}/planted.md", content="x")[0],
            str(person.tree(target).status_code),
            str(person.upload(f"{target}/planted.bin", b"x").status_code),
            str(len(person.tool("search", query="private of")[1]["hits"])),
        ]
        return seen

    answers = together(
        *(
            lambda p=person, n=number: work(p, homes[n], homes[(n + 1) % PEOPLE])
            for number, person in enumerate(crowd)
        )
    )
    assert all(
        seen == ["ok", "unavailable", "unavailable", "unavailable", "404", "404", "1"]
        for seen in answers
    ), answers
    for number, home in enumerate(homes):
        assert sorted(p.name for p in (team.root / home[1:]).iterdir()) == [
            ".brainfold.toml",
            "secret.md",
        ]
        assert text(team, f"{home}/secret.md") == f"private of {crowd[number].email}"
    # git attributes each private file to its owner and to nobody else.
    for number, home in enumerate(homes):
        authors = set(git(team, "log", "--format=%an", "--", f"{home[1:]}/secret.md").split())
        assert authors == {crowd[number].email}


def test_access_flipping_under_writers_never_lets_a_revoked_write_through(
    team: Team, crowd: list[Person]
) -> None:
    """An administrator takes a group out and puts it back while its members hammer one
    folder. Every acknowledged write must be on disk and in git; every refusal must be a
    clean permission answer; and nothing written is ever attributed to someone who was
    out of the group when the server accepted it."""
    team.admin.tool("create_folder", path="/flip", description="Flips.")
    inside, outside = crowd[:5], crowd[5:]
    team.group("flippers", *inside)
    team.access("/flip", ["@flippers"], ["@flippers"], "Flips.")
    stop = threading.Event()
    wrong: list[str] = []
    done: dict[str, str] = {}
    lock = threading.Lock()

    def hammer(person: Person, number: int) -> None:
        count = 0
        while not stop.is_set():
            count += 1
            path = f"/flip/{number}-{count}.md"
            code, result = person.tool("write", path=path, content=person.email)
            if code == "ok":
                with lock:
                    done[path] = person.email
            elif code not in {"unavailable", "write_denied"}:
                wrong.append(f"{person.email}: {result}")
            code, result = person.tool("list", path="/flip")
            if code not in {"ok", "unavailable"}:
                wrong.append(f"{person.email}: {result}")

    threads = [
        threading.Thread(target=hammer, args=(person, number))
        for number, person in enumerate(crowd)
    ]
    for thread in threads:
        thread.start()
    for round_number in range(12):
        members = outside if round_number % 2 else inside
        assert team.group("flippers", *members).status_code == 200
        if round_number % 3 == 0:
            assert team.access("/flip", ["@flippers"], [], "Flips.").status_code == 200
            assert team.access("/flip", ["@flippers"], ["@flippers"], "Flips.").status_code == 200
    # Final state: only `outside` are members. From here no insider write may succeed.
    stop.set()
    for thread in threads:
        thread.join(60)
    assert not wrong, wrong[:5]
    assert done, "the test never saw a successful write"
    for person in inside:
        assert person.tool("write", path="/flip/after.md", content="x")[0] == "write_denied"
        assert person.tool("read", path=next(iter(done)))[0] == "unavailable"
    on_disk = {f"/flip/{p.name}" for p in (team.root / "flip").glob("*.md")}
    assert on_disk == set(done)
    for path, author in random.sample(sorted(done.items()), min(20, len(done))):
        assert text(team, path) == author
        assert git(team, "log", "--format=%an", "--", path[1:]).split() == [author]


def test_a_person_removed_in_the_middle_of_their_work_stops_cleanly(
    team: Team, crowd: list[Person]
) -> None:
    victim = team.join("leaving@atlas.test")
    team.group("writers", *crowd, victim)
    session_two = team.login(victim.email)
    stop = threading.Event()
    seen: list[str] = []
    removed = threading.Event()
    late: list[str] = []

    def work(number: int) -> None:
        count = 0
        while not stop.is_set():
            count += 1
            was_removed = removed.is_set()
            code, _ = victim.tool("append", path=f"/shared/leaving-{number}.md", content=str(count))
            status = session_two.tree("/shared").status_code
            seen.extend([code, str(status)])
            if was_removed and (code == "ok" or status == 200):
                late.append(f"{code} {status}")

    threads = [threading.Thread(target=work, args=(number,)) for number in range(4)]
    for thread in threads:
        thread.start()
    while seen.count("ok") < 8:
        time.sleep(0.01)
    assert team.admin.panel.delete(f"/api/users/{victim.email}").status_code == 200
    removed.set()
    while seen.count("unauthenticated") < 8:
        time.sleep(0.01)
    stop.set()
    for thread in threads:
        thread.join(60)
    # A call already past the door when the account went finds nothing: it fails closed.
    assert {"ok", "200", "unauthenticated", "401"} <= set(seen), Counter(seen)
    assert set(seen) <= {
        "ok",
        "200",
        "unauthenticated",
        "401",
        "unavailable",
        "write_denied",
        "404",
    }, Counter(seen)
    assert not late, late
    # Everything acknowledged before the removal is intact and under their name.
    for number in range(4):
        lines = text(team, f"/shared/leaving-{number}.md").split()
        assert lines == [str(n) for n in range(1, len(lines) + 1)]
    assert team.group("writers", *crowd).status_code == 200


def test_a_first_visit_from_many_tabs_and_agents_creates_one_personal_folder(
    team: Team,
) -> None:
    invite = team.invite("newcomer@atlas.test")
    person = Person(team.base, "newcomer@atlas.test")
    person.panel.post("/api/accept", json={"invite": invite, "password": "a-long-password"})
    person.connect()
    answers = together(
        *([lambda: person.tool("list")[1]["home"]] * 5 + [lambda: person.tree().json()["home"]] * 5)
    )
    assert len(set(answers)) == 1
    homes = [p.name for p in (team.root / "people").iterdir() if p.name.startswith("newcomer-")]
    assert homes == [answers[0].rsplit("/", 1)[-1]]
    assert commits(team, f"/people/{homes[0]}/.brainfold.toml") == 1
