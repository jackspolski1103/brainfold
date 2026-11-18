"""A whole team on a real server: what each person sees, invitations, and revocation.

Every check runs through both doors a person has: the panel (session cookie) and the
harness (MCP and /files with a token). See `team.py` for the helpers.
"""

from __future__ import annotations

import sqlite3
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from team import ADMIN, PASSWORD, Person, Team, serving, together

ALICE, BOB, CAROL, DAVE, DANA, ERIN = (
    f"{name}@atlas.test" for name in ("alice", "bob", "carol", "dave", "dana", "erin")
)
SKILL = "---\nname: deploy\ndescription: Deploy the service.\n---\n1. Ship it.\n"

# path -> the people who can read it. Everyone else must see nothing at all.
READERS = {
    "/common/handbook.md": {ADMIN, ALICE, BOB, CAROL, DAVE, DANA, ERIN},
    "/finance/budget.md": {ALICE, BOB},
    "/finance/payroll/salaries.md": {ALICE},
    "/eng/design.md": {CAROL, DAVE},
    "/eng/deploy/SKILL.md": {CAROL, DAVE},
    "/direct/note.md": {DANA},
    "/locked/vault.md": set(),
}
WRITERS = {
    "/common/handbook.md": {ADMIN},
    "/finance/budget.md": {ALICE, BOB},
    "/finance/payroll/salaries.md": {ALICE},
    "/eng/design.md": {CAROL},
    "/eng/deploy/SKILL.md": {CAROL},
    "/direct/note.md": {DANA},
    "/locked/vault.md": set(),
}
SECRET = {path: f"secret-{index}-zebra" for index, path in enumerate(READERS)}


def seed(root: Path) -> None:
    for path, word in SECRET.items():
        target = root / path[1:]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(SKILL + word if path.endswith("SKILL.md") else f"# {word}\n", "utf-8")
    rules = {
        "": 'read = ["*"]\nwrite = ["admin@atlas.test"]\n',
        "finance": 'read = ["@finance"]\nwrite = ["@finance"]\n',
        "finance/payroll": 'read = ["@payroll"]\n',
        "eng": 'read = ["@eng"]\nwrite = ["@eng-leads"]\n',
        "direct": 'read = ["dana@atlas.test"]\nwrite = ["dana@atlas.test"]\n',
        "locked": "read = []\nwrite = []\n",
    }
    for folder, text in rules.items():
        (root / folder / ".brainfold.toml").write_text(text, "utf-8")


@pytest.fixture
def team(tmp_path: Path) -> Iterator[Team]:
    seed(tmp_path / "brain")
    with serving(tmp_path / "brain", tmp_path / "brainfold.db") as team:
        yield team


@pytest.fixture
def people(team: Team) -> dict[str, Person]:
    everyone = {email: team.join(email) for email in (ALICE, BOB, CAROL, DAVE, DANA, ERIN)}
    team.group("finance", ALICE, BOB)
    team.group("payroll", ALICE)
    team.group("eng", CAROL, DAVE)
    team.group("eng-leads", CAROL)
    return everyone | {ADMIN: team.admin}


def code(response: httpx.Response) -> str:
    return response.json()["error"]["code"]


def sees(person: Person, path: str) -> bool:
    """Whether a person reaches a file through any door. Every door must agree."""
    word = SECRET.get(path, "zebra")
    folder = path.rsplit("/", 1)[0] or "/"
    listed = person.tree(folder)
    found = person.tool("search", query=word)
    doors = {
        "panel file": person.file(path).status_code == 200,
        "panel download": person.download(path).status_code == 200,
        "panel tree": listed.status_code == 200
        and any(e["path"] == path and "size" in e for e in listed.json()["entries"]),
        "panel search": any(
            hit["path"] == path
            for hit in person.panel.get("/api/search", params={"q": word}).json()["hits"]
        ),
        "mcp read": person.tool("read", path=path)[0] == "ok",
        "mcp list": (inside := person.tool("list", path=folder))[0] == "ok"
        and any(e["path"] == path for e in inside[1]["entries"]),
        "mcp search": found[0] == "ok" and any(hit["path"] == path for hit in found[1]["hits"]),
        "files get": person.agent.get(f"/files{path}").status_code == 200,
    }
    assert len(set(doors.values())) == 1, f"{person.email} {path}: the doors disagree: {doors}"
    return doors["mcp read"]


def git(team: Team, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(team.root), *args], capture_output=True, text=True, check=True
    )
    return done.stdout


def assert_sound(team: Team) -> None:
    """After anything: every change is in git, nothing half-written is left behind."""
    assert team.health()["unversioned_writes"] == 0
    assert git(team, "status", "--porcelain") == ""
    assert not list(team.root.rglob("*.brainfold-tmp"))
    assert "error" not in git(team, "fsck", "--no-dangling").lower()


# --- what each person sees ------------------------------------------------------------


def test_every_person_reads_exactly_what_they_were_granted_through_every_door(
    team: Team, people: dict[str, Person]
) -> None:
    for email, person in people.items():
        for path, readers in READERS.items():
            assert sees(person, path) == (email in readers), f"{email} {path}"


def test_a_denied_path_answers_exactly_like_a_path_that_does_not_exist(
    team: Team, people: dict[str, Person]
) -> None:
    erin = people[ERIN]  # an account with no group at all
    for hidden, absent in (
        ("/finance/budget.md", "/finance/nothing.md"),
        ("/finance", "/nowhere"),
        ("/locked/vault.md", "/locked/nothing.md"),
        (f"/people/{people[ALICE].tool('list')[1]['home'].rsplit('/')[-1]}", "/people/ghost-0000"),
    ):
        for call in (
            lambda p: (erin.tree(p).status_code, erin.tree(p).json()),
            lambda p: (erin.file(p).status_code, erin.file(p).json()),
            lambda p: (erin.download(p).status_code, erin.download(p).json()),
            lambda p: (
                erin.agent.get(f"/files{p}").status_code,
                erin.agent.get(f"/files{p}").json(),
            ),
            lambda p: (
                erin.upload(f"{p}/x.bin", b"x").status_code,
                erin.upload(f"{p}/x.bin", b"x").json(),
            ),
        ):
            assert call(hidden) == call(absent), hidden
        for tool, arguments in (
            ("list", {}),
            ("read", {}),
            ("history", {}),
            ("write", {"content": "x"}),
            ("write", {"content": "x", "version": "0" * 64}),
            ("edit", {"old": "a", "new": "b"}),
            ("append", {"content": "x"}),
            ("delete", {"version": "0" * 64}),
            ("delete", {}),
            ("describe_file", {"description": "x"}),
            ("describe_folder", {"description": "x"}),
            ("create_folder", {"description": "x"}),
            ("restore", {"revision": 1}),
            ("search", {"query": "zebra"}),
        ):
            assert erin.tool(tool, path=hidden, **arguments) == erin.tool(
                tool, path=absent, **arguments
            ), f"{tool} {hidden}"
        for tool, arguments in (
            ("move", {"source": hidden, "destination": "/common/x.md", "version": "0" * 64}),
            ("move", {"source": "/common/handbook.md", "destination": f"{hidden}/x.md"}),
        ):
            other = {k: v.replace(hidden, absent) for k, v in arguments.items()}
            assert erin.tool(tool, **arguments) == erin.tool(tool, **other), f"{tool} {hidden}"
    # Nothing was created or changed by all those attempts.
    assert git(team, "status", "--porcelain") == ""
    assert not (team.root / "finance" / "x.bin").exists()


def test_only_those_granted_write_can_change_a_file_through_any_door(
    team: Team, people: dict[str, Person]
) -> None:
    for path, writers in WRITERS.items():
        for email, person in people.items():
            folder = path.rsplit("/", 1)[0]
            allowed = email in writers
            readable = email in READERS[path]
            # Without read, the answer is the one a missing folder would give there:
            # "no write" where the nearest folder they see is read-only for them, and
            # "not available" where they could have created it (the administrator at the
            # root, Bob in /finance next to the payroll folder he cannot see).
            creatable = not readable and (
                email == ADMIN or (email == BOB and path.startswith("/finance/payroll/"))
            )
            denied = "unavailable" if creatable else "write_denied"
            refused = 404 if creatable else 403
            listing = person.tool("list", path=folder)
            assert (listing[0] == "ok" and listing[1]["can_write"]) == allowed, (email, path)
            new = f"{folder}/by-{email.split('@')[0]}.md"
            for outcome in (
                person.tool("write", path=new, content="x")[0],
                person.tool("append", path=f"{new}.log", content="x")[0],
                person.tool("create_folder", path=f"{new}.d", description="x")[0],
                person.tool("describe_file", path=path, description="x")[0],
                person.tool("describe_folder", path=folder, description="x")[0],
            ):
                assert outcome == ("ok" if allowed else denied), (email, path, outcome)
            status = person.upload(f"{new}.bin", b"\x00").status_code
            assert status == (200 if allowed else refused), (email, path)
            status = person.agent.put(f"/files{new}.bin2", content=b"\x00").status_code
            assert status == (200 if allowed else refused), (email, path)
    # The refusal tells a reader who can change it, and tells a non-reader exactly what a
    # folder that does not exist would.
    assert ADMIN in people[DAVE].tool("write", path="/eng/x.md", content="x")[1]
    assert people[ERIN].tool("write", path="/eng/x.md", content="x") == people[ERIN].tool(
        "write", path="/absent/x.md", content="x"
    )
    assert_sound(team)


def test_an_administrator_manages_every_folder_but_reads_only_what_was_granted(
    team: Team, people: dict[str, Person]
) -> None:
    admin = team.admin
    root = admin.tree("/").json()
    assert {e["path"] for e in root["entries"]} >= {"/finance", "/eng", "/direct", "/locked"}
    finance = admin.tree("/finance").json()
    assert finance["read"] == ["@finance"] and finance["can_write"] is False
    # Names of files are structure; size, description and content are not.
    assert {"path": "/finance/budget.md", "kind": "file"} in finance["entries"]
    # An ordinary token of an administrator is an ordinary member: no manage mode.
    assert admin.tool("list", path="/finance")[0] == "unavailable"
    assert "/finance" not in {e["path"] for e in admin.tool("list")[1]["entries"]}
    # Personal folders: an administrator sees that they exist and nothing else.
    home = people[ALICE].tool("list")[1]["home"]
    people[ALICE].tool("write", path=f"{home}/diary.md", content="zebra private")
    assert home in {e["path"] for e in admin.tree("/people").json()["entries"]}
    assert admin.tree(home).status_code == 404
    assert admin.file(f"{home}/diary.md").status_code == 404
    assert admin.download(f"{home}/diary.md").status_code == 404
    assert code(team.access(home, ["*"], ["*"])) == "unavailable"
    assert admin.tool("history", path=f"{home}/diary.md")[0] == "no_history"
    # Members never see other people's personal folders, not even their names.
    for email in (BOB, ERIN):
        assert [e["path"] for e in people[email].tree("/people").json()["entries"]] == [
            people[email].tool("list")[1]["home"]
        ]
    # Granting oneself is possible, visible and recorded.
    assert team.access("/finance", ["@finance", ADMIN], ["@finance"]).status_code == 200
    assert admin.file("/finance/budget.md").status_code == 200
    log = admin.panel.get("/api/activity").json()["activity"]
    assert any(row["action"] == "edit_access" and row["path"] == "/finance" for row in log)


def test_members_and_strangers_cannot_use_any_administration_route(
    team: Team, people: dict[str, Person]
) -> None:
    stranger = httpx.Client(base_url=team.base)
    forged = httpx.Client(base_url=team.base, cookies={"brainfold_session": "brainfold_forged"})
    # A harness token is not a panel session, wherever it is put.
    token_as_cookie = httpx.Client(
        base_url=team.base, cookies={"brainfold_session": people[ALICE].token}
    )
    token_as_bearer = people[ALICE].agent
    admin_routes = [
        ("GET", "/api/users", None),
        ("POST", "/api/users", {"email": "mallory@atlas.test", "role": "admin"}),
        ("DELETE", f"/api/users/{BOB}", None),
        ("POST", f"/api/users/{ADMIN}/reset", {}),
        ("GET", "/api/groups", None),
        ("PUT", "/api/groups/finance", {"members": [ERIN]}),
        ("PUT", "/api/folder", {"path": "/", "read": ["*"], "write": ["*"]}),
        ("GET", "/api/activity", None),
    ]
    member_routes = [
        ("GET", "/api/tree", None),
        ("GET", "/api/file?path=/common/handbook.md", None),
        ("GET", "/api/files?path=/common/handbook.md", None),
        ("GET", "/api/search?q=zebra", None),
        ("GET", "/api/skills", None),
        ("GET", "/api/tokens", None),
        ("POST", "/api/tokens", {"name": "x"}),
        ("POST", "/api/logout", {}),
        ("POST", "/api/password", {"current": PASSWORD, "new": PASSWORD + "2"}),
        ("PUT", "/api/describe", {"path": "/common/handbook.md", "description": "x"}),
    ]
    for method, url, body in admin_routes:
        for email in (ALICE, ERIN):
            response = people[email].panel.request(method, url, json=body)
            assert response.status_code == 403, (email, method, url)
    for method, url, body in admin_routes + member_routes:
        for client in (stranger, forged, token_as_cookie, token_as_bearer):
            assert client.request(method, url, json=body).status_code == 401, (method, url)
    # And the panel session is not a harness token.
    session = people[ALICE].panel.cookies["brainfold_session"]
    as_agent = Person(team.base, ALICE)
    as_agent.agent.headers["Authorization"] = f"Bearer {session}"
    assert as_agent.tool("list")[0] == "unauthenticated"
    assert as_agent.agent.get("/files/common/handbook.md").status_code == 401
    # Nothing above took effect.
    users = {user["email"]: user for user in team.admin.panel.get("/api/users").json()["users"]}
    assert "mallory@atlas.test" not in users and BOB in users
    assert users[ERIN]["groups"] == []
    assert team.admin.tree("/").json()["write"] == [ADMIN]
    # Each person sees and revokes only their own tokens.
    alice, bob = people[ALICE], people[BOB]
    theirs = bob.panel.get("/api/tokens").json()["tokens"]
    assert [token["name"] for token in theirs] == ["harness"]
    alice.panel.delete(f"/api/tokens/{theirs[0]['id']}")
    assert bob.tool("list")[0] == "ok"
    for row in alice.panel.get("/api/tokens").json()["tokens"]:
        assert set(row) == {"id", "name", "created", "last_used", "manage"}  # never the token


def test_each_agent_is_offered_only_the_skills_its_person_can_read(
    team: Team, people: dict[str, Person]
) -> None:
    def offered(person: Person) -> set[str]:
        panel = {s["name"] for s in person.panel.get("/api/skills").json()["skills"]}
        listing = person.agent.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            headers={"Accept": "application/json, text/event-stream"},
        ).json()["result"]["tools"]
        text = next(tool["description"] for tool in listing if tool["name"] == "use_skill")
        for name in panel:
            assert name in text
        assert ("deploy-" in text) == any(name.startswith("deploy-") for name in panel)
        return {name.rsplit("-", 1)[0] for name in panel}

    for email, person in people.items():
        expected = {"propose", "deploy"} if email in {CAROL, DAVE} else {"propose"}
        assert offered(person) == expected, email
        assert (person.tool("use_skill", name="deploy")[0] == "ok") == (email in {CAROL, DAVE})
    # Losing the folder takes the skill away at once.
    team.group("eng", CAROL)
    assert offered(people[DAVE]) == {"propose"}
    refused = people[DAVE].tool("use_skill", name="deploy")
    assert refused[0] == "unavailable" and "deploy" not in refused[1].partition("Your skills")[2]


# --- invitations ----------------------------------------------------------------------


def test_an_invitation_works_once_for_one_person_and_only_until_it_is_withdrawn(
    team: Team,
) -> None:
    admin = team.admin.panel
    invite = team.invite("Frank@Atlas.test ")  # stored trimmed and in lower case
    frank = "frank@atlas.test"
    listed = {user["email"]: user for user in admin.get("/api/users").json()["users"]}
    assert listed[frank] == {"email": frank, "role": "member", "pending": True, "groups": []}
    # Before accepting there is no way in: no password, and the link is not a credential.
    visitor = httpx.Client(base_url=team.base)
    for password in ("", PASSWORD, invite, "None"):  # four: a fifth failure locks the email
        response = visitor.post("/api/login", json={"email": frank, "password": password})
        assert response.status_code == 400 and code(response) == "invalid_credentials"
    as_session = httpx.Client(base_url=team.base, cookies={"brainfold_session": invite})
    assert as_session.get("/api/tree").status_code == 401
    as_token = httpx.Client(base_url=team.base, headers={"Authorization": f"Bearer {invite}"})
    assert as_token.get("/files/common/handbook.md").status_code == 401
    # The same email cannot be invited twice, in any spelling.
    for spelling in (frank, "FRANK@atlas.test"):
        assert code(admin.post("/api/users", json={"email": spelling})) == "already_exists"
    # Bad input never creates an account, and never burns the link.
    for body in (
        {"email": "not-an-email"},
        {"email": "a@b", "role": "owner"},
        {"email": ["x@y.z"]},
        {"email": None},
        {},
    ):
        assert admin.post("/api/users", json=body).status_code == 400, body
    for password in ("short", "", None, 12345678901, "x" * 257):
        refused = visitor.post("/api/accept", json={"invite": invite, "password": password})
        assert refused.status_code == 400 and code(refused) == "invalid_password"
    for wrong in ("", invite[:-1], invite + "x", None, 7):
        refused = visitor.post("/api/accept", json={"invite": wrong, "password": PASSWORD})
        assert refused.status_code == 400 and code(refused) == "invalid_invite"
    assert visitor.get("/api/state").json()["user"] is None
    # Accepting signs the person in as a member, with a personal folder and nothing else.
    accepted = visitor.post("/api/accept", json={"invite": invite, "password": PASSWORD})
    assert accepted.status_code == 200
    assert visitor.get("/api/state").json()["user"] == {"email": frank, "role": "member"}
    assert visitor.get("/api/users").status_code == 403
    # The link is spent: it cannot set another password or sign anyone else in.
    thief = httpx.Client(base_url=team.base)
    again = thief.post("/api/accept", json={"invite": invite, "password": "another-password"})
    assert code(again) == "invalid_invite"
    assert team.login(frank).tree().status_code == 200
    assert code(thief.post("/api/login", json={"email": frank, "password": "another-password"}))

    # A withdrawn invitation is dead, and a new one for the same email is a new account.
    first = team.invite(GRACE := "grace@atlas.test")
    assert admin.delete(f"/api/users/{GRACE}").status_code == 200
    assert code(visitor.post("/api/accept", json={"invite": first, "password": PASSWORD})) == (
        "invalid_invite"
    )
    second = team.invite(GRACE)
    assert code(visitor.post("/api/accept", json={"invite": first, "password": PASSWORD})) == (
        "invalid_invite"
    )
    # A fresh link for someone still pending replaces the one that got lost.
    third = admin.post(f"/api/users/{GRACE}/reset", json={}).json()["invite"]
    assert code(visitor.post("/api/accept", json={"invite": second, "password": PASSWORD})) == (
        "invalid_invite"
    )
    assert (
        visitor.post("/api/accept", json={"invite": third, "password": PASSWORD}).status_code == 200
    )


def test_an_invited_administrator_administers_and_an_invited_member_does_not(
    team: Team,
) -> None:
    second = team.join("root2@atlas.test", "admin")
    member = team.join(ERIN)
    assert second.panel.get("/api/users").status_code == 200
    assert member.panel.get("/api/users").status_code == 403
    # A member cannot mint an administrator, not even by inviting.
    assert (
        member.panel.post("/api/users", json={"email": "x@y.z", "role": "admin"}).status_code == 403
    )
    # Two administrators: either can remove the other, but one always remains.
    assert second.panel.delete(f"/api/users/{ADMIN}").status_code == 200
    assert team.admin.panel.get("/api/state").json()["user"] is None
    assert code(second.panel.delete("/api/users/root2@atlas.test")) == "last_admin"


def test_many_people_using_the_same_invitation_at_once_create_one_account(team: Team) -> None:
    invite = team.invite(ERIN)
    clients = [httpx.Client(base_url=team.base, timeout=60) for _ in range(8)]
    answers = together(
        *(
            lambda c=client, n=number: c.post(
                "/api/accept", json={"invite": invite, "password": f"password-number-{n}"}
            )
            for number, client in enumerate(clients)
        )
    )
    winners = [n for n, answer in enumerate(answers) if answer.status_code == 200]
    assert len(winners) == 1, [answer.text for answer in answers]
    assert all(code(a) == "invalid_invite" for a in answers if a.status_code != 200)
    # Only the winner's password opens the account, and only the winner is signed in.
    for number, client in enumerate(clients):
        signed_in = client.get("/api/state").json()["user"]
        assert (signed_in is not None) == (number == winners[0])
    assert team.login(ERIN, f"password-number-{winners[0]}").tree().status_code == 200


def test_simultaneous_administration_never_leaves_two_of_anything(team: Team) -> None:
    admin = team.admin.panel
    invited = together(*(lambda: admin.post("/api/users", json={"email": ERIN}) for _ in range(8)))
    assert sorted(a.status_code for a in invited) == [200] + [409] * 7
    assert [u["email"] for u in admin.get("/api/users").json()["users"]] == [ADMIN, ERIN]
    alice, bob = team.join(ALICE), team.join(BOB)
    # Two saves of the same group at once: one of the two lists, never a mix or an error.
    saved = together(
        *(lambda m=members: team.group("finance", *m) for members in ([ALICE], [BOB]) * 6)
    )
    assert all(answer.status_code == 200 for answer in saved)
    assert admin.get("/api/groups").json()["groups"]["finance"] in ([ALICE], [BOB])
    # The first account can only be created once (checked on a second, empty server below).
    assert code(admin.post("/api/setup", json={"email": "x@y.z", "password": PASSWORD})) == (
        "already_set_up"
    )
    assert alice.tree().status_code == bob.tree().status_code == 200


def test_the_first_account_is_created_once_even_when_several_people_race(tmp_path: Path) -> None:
    from team import Team as Plain

    original = Plain.__init__
    Plain.__init__ = lambda self, base, root, app: setattr(self, "base", base)  # no auto setup
    try:
        with serving(tmp_path / "brain", tmp_path / "db") as empty:
            clients = [httpx.Client(base_url=empty.base, timeout=60) for _ in range(6)]
            answers = together(
                *(
                    lambda c=client, n=number: c.post(
                        "/api/setup", json={"email": f"p{n}@atlas.test", "password": PASSWORD}
                    )
                    for number, client in enumerate(clients)
                )
            )
            assert sorted(a.status_code for a in answers) == [200] + [400] * 5
            winner = next(c for c, a in zip(clients, answers, strict=True) if a.status_code == 200)
            users = winner.get("/api/users").json()["users"]
            assert len(users) == 1 and users[0]["role"] == "admin"
    finally:
        Plain.__init__ = original


# --- revocation -----------------------------------------------------------------------


def test_taking_a_folder_away_closes_every_door_at_once_and_giving_it_back_reopens_them(
    team: Team, people: dict[str, Person]
) -> None:
    bob, alice = people[BOB], people[ALICE]
    path = "/finance/budget.md"
    assert bob.tool("edit", path=path, old="secret", new="Secret")[0] == "ok"
    before = bob.tool("read", path=path)[1]
    assert bob.tool("append", path="/finance/LEARNINGS.md", content="zebra learning")[0] == "ok"
    assert bob.tool("history", path=path)[0] == "ok"
    assert sees(bob, path)

    def closed(person: Person) -> None:
        assert not sees(person, path)
        assert person.tree("/finance").status_code == 404
        assert "/finance" not in {e["path"] for e in person.tree("/").json()["entries"]}
        assert person.tool("history", path=path)[0] == "no_history"
        assert person.tool("list_learnings")[1]["learnings"] == []
        # A version read while access lasted is worth nothing afterwards: every attempt
        # gets the answer a folder that never existed would give.
        absent = person.tool("write", path="/never-existed/new.md", content="late")
        assert absent[0] in {"write_denied", "unavailable"}
        for attempt in (
            person.tool("write", path=path, content="late", version=before["version"]),
            person.tool("edit", path=path, old="Secret", new="late"),
            person.tool("append", path=path, content="late"),
            person.tool("delete", path=path, version=before["version"]),
            person.tool("move", source=path, destination="/x.md", version=before["version"]),
            person.tool("restore", path=path, revision=1, version=before["version"]),
            person.tool("write", path="/finance/new.md", content="late"),
        ):
            assert attempt[0] == absent[0], attempt
        refused = person.upload("/never-existed/new.bin", b"late").status_code
        assert refused in {403, 404}
        assert person.upload(path, b"late", before["version"]).status_code == refused
        assert person.agent.put(f"/files{path}", content=b"late").status_code == refused

    # 1. The administrator rewrites the folder's read list.
    assert team.access("/finance", ["@payroll"], ["@payroll"]).status_code == 200
    closed(bob)
    assert sees(alice, path)  # alice is in @payroll, bob is not
    assert team.access("/finance", ["@finance"], ["@finance"]).status_code == 200
    assert sees(bob, path) and bob.tool("history", path=path)[0] == "ok"
    # 2. The administrator takes the person out of the group.
    assert team.group("finance", ALICE).status_code == 200
    closed(bob)
    assert sees(alice, path)
    team.group("finance", ALICE, BOB)
    assert sees(bob, path)
    # 3. A folder above narrows: everything below goes with it.
    assert team.access("/", [ALICE, ADMIN], [ADMIN]).status_code == 200
    closed(bob)
    assert not sees(bob, "/common/handbook.md")
    home = bob.tool("list")[1]["home"]  # the personal folder always stays reachable
    assert bob.tool("write", path=f"{home}/still.md", content="mine")[0] == "ok"
    assert sees(alice, path)
    team.access("/", ["*"], [ADMIN])
    # 4. The group is deleted: its name is retired and cannot be handed to anyone.
    assert team.group("finance").status_code == 200
    closed(bob)
    closed(alice)
    assert code(team.group("finance", ERIN)) == "invalid_group"
    assert not sees(people[ERIN], path)
    # The file itself was never touched by any of the late attempts.
    assert (team.root / "finance" / "budget.md").read_text("utf-8") == before["content"]
    assert_sound(team)


def test_write_can_be_taken_away_while_read_stays(team: Team, people: dict[str, Person]) -> None:
    carol, dave = people[CAROL], people[DAVE]
    version = carol.tool("read", path="/eng/design.md")[1]["version"]
    assert team.group("eng-leads", DAVE).status_code == 200  # carol out, dave in
    assert sees(carol, "/eng/design.md")
    assert carol.tree("/eng").json()["can_write"] is False
    for attempt in (
        carol.tool("write", path="/eng/design.md", content="late", version=version),
        carol.tool("edit", path="/eng/design.md", old="secret", new="late"),
        carol.tool("append", path="/eng/design.md", content="late"),
        carol.tool("delete", path="/eng/design.md", version=version),
        carol.tool("move", source="/eng/design.md", destination="/eng/d2.md", version=version),
        carol.tool("create_folder", path="/eng/new", description="x"),
        carol.tool("describe_folder", path="/eng", description="x"),
        carol.tool("describe_file", path="/eng/design.md", description="x"),
    ):
        assert attempt[0] == "write_denied" and ADMIN in attempt[1], attempt
    assert carol.upload("/eng/design.md", b"late", version).status_code == 403
    assert (
        carol.panel.put(
            "/api/describe", json={"path": "/eng/design.md", "description": "x"}
        ).status_code
        == 403
    )
    assert dave.tool("write", path="/eng/design.md", content="dave", version=version)[0] == "ok"
    # A subfolder that declares its own write keeps it: nearest declaration wins.
    team.access("/eng/deploy", None, [CAROL])
    assert carol.tool("write", path="/eng/deploy/notes.md", content="x")[0] == "ok"
    assert dave.tool("write", path="/eng/deploy/more.md", content="x")[0] == "write_denied"
    assert_sound(team)


def test_removing_a_person_ends_every_session_and_token_and_nothing_brings_them_back(
    team: Team, people: dict[str, Person]
) -> None:
    dana = people[DANA]
    second_session = team.login(DANA)
    second_token = Person(team.base, DANA)
    second_token.panel = second_session.panel
    second_token.connect("second harness")
    home = dana.tool("list")[1]["home"]
    dana.tool("write", path=f"{home}/diary.md", content="zebra diary")
    note = dana.tool("read", path="/direct/note.md")[1]
    dana.tool("write", path="/direct/note.md", content="by dana", version=note["version"])
    reset = team.admin.panel.post(f"/api/users/{DANA}/reset", json={}).json()["invite"]

    assert team.admin.panel.delete(f"/api/users/{DANA}").status_code == 200

    for person in (dana, second_session, second_token):
        assert person.tree().status_code == 401
        assert person.file("/common/handbook.md").status_code == 401
        assert person.panel.get("/api/tokens").status_code == 401
        assert person.panel.post("/api/tokens", json={"name": "again"}).status_code == 401
        assert person.panel.get("/api/state").json()["user"] is None
    for person in (dana, second_token):
        assert person.tool("list")[0] == "unauthenticated"
        assert person.tool("read", path=f"{home}/diary.md")[0] == "unauthenticated"
        assert person.agent.get("/files/common/handbook.md").status_code == 401
        assert person.agent.put(f"/files{home}/x.bin", content=b"x").status_code == 401
    visitor = httpx.Client(base_url=team.base)
    assert code(visitor.post("/api/login", json={"email": DANA, "password": PASSWORD})) == (
        "invalid_credentials"
    )
    # A reset link issued before the removal died with the account.
    assert code(visitor.post("/api/accept", json={"invite": reset, "password": PASSWORD})) == (
        "invalid_invite"
    )
    users = [user["email"] for user in team.admin.panel.get("/api/users").json()["users"]]
    assert DANA not in users
    # What they wrote stays; their personal folder stays on disk, closed to everyone.
    assert (team.root / "direct" / "note.md").read_text("utf-8") == "by dana"
    assert (team.root / home[1:] / "diary.md").is_file()
    assert team.admin.tree(home).status_code == 404
    for person in (people[ALICE], team.admin):
        assert person.tool("read", path=f"{home}/diary.md")[0] == "unavailable"
        assert person.tool("search", query="zebra diary")[1]["hits"] == []

    # The same email invited again is a new account: new personal folder, no old groups,
    # and no history from before it existed.
    team.group("payroll", ALICE, BOB)
    back = team.join(DANA)
    new_home = back.tool("list")[1]["home"]
    assert new_home != home
    assert back.tool("read", path=f"{home}/diary.md")[0] == "unavailable"
    assert back.tree(home).status_code == 404
    listed = {user["email"]: user for user in team.admin.panel.get("/api/users").json()["users"]}
    assert listed[DANA]["groups"] == []
    assert_sound(team)


def test_a_removed_person_is_also_removed_from_the_folders_that_named_them(
    team: Team, people: dict[str, Person]
) -> None:
    """Removing someone must end their access for good: if the same address is invited
    again later, it starts with nothing until an administrator grants it again."""
    assert sees(people[DANA], "/direct/note.md")
    assert team.admin.panel.delete(f"/api/users/{DANA}").status_code == 200
    back = team.join(DANA)
    assert not sees(back, "/direct/note.md")
    assert back.tool("write", path="/direct/new.md", content="x")[0] == "write_denied"


def test_one_token_or_one_session_can_end_without_touching_the_others(
    team: Team, people: dict[str, Person]
) -> None:
    alice = people[ALICE]
    laptop, phone = team.login(ALICE), team.login(ALICE)
    other = Person(team.base, ALICE)
    other.panel = laptop.panel
    other.connect("codex")
    names = {t["name"]: t["id"] for t in alice.panel.get("/api/tokens").json()["tokens"]}
    assert set(names) == {"harness", "codex"}
    # Revoking one token: that harness stops, the other and the panel go on.
    assert alice.panel.delete(f"/api/tokens/{names['codex']}").status_code == 200
    assert other.tool("list")[0] == "unauthenticated"
    assert other.agent.get("/files/common/handbook.md").status_code == 401
    assert alice.tool("list")[0] == "ok" and laptop.tree().status_code == 200
    # Signing out one browser leaves the others signed in.
    assert phone.panel.post("/api/logout", json={}).status_code == 200
    assert phone.tree().status_code == 401
    assert laptop.tree().status_code == 200 and alice.tree().status_code == 200
    # Changing the password signs out every other browser and revokes the harness tokens:
    # whoever held the old password may have created one (decision 0015).
    changed = laptop.panel.post(
        "/api/password", json={"current": PASSWORD, "new": "a-new-password"}
    )
    assert changed.status_code == 200
    assert laptop.tree().status_code == 200
    assert alice.tree().status_code == 401
    assert alice.tool("list")[0] == "unauthenticated"
    visitor = httpx.Client(base_url=team.base)
    assert code(visitor.post("/api/login", json={"email": ALICE, "password": PASSWORD})) == (
        "invalid_credentials"
    )
    # A reset link: the old password works until it is used, then everything signs out.
    link = team.admin.panel.post(f"/api/users/{ALICE}/reset", json={}).json()["invite"]
    assert team.login(ALICE, "a-new-password").tree().status_code == 200
    assert (
        visitor.post("/api/accept", json={"invite": link, "password": "third-password"}).status_code
        == 200
    )
    assert laptop.tree().status_code == 401
    assert (
        code(
            httpx.Client(base_url=team.base).post(
                "/api/login", json={"email": ALICE, "password": "a-new-password"}
            )
        )
        == "invalid_credentials"
    )
    # Nobody else was signed out by any of this.
    assert people[BOB].tree().status_code == 200 and people[BOB].tool("list")[0] == "ok"


def test_history_shows_a_person_only_the_revisions_they_could_read_then_and_can_read_now(
    team: Team, people: dict[str, Person]
) -> None:
    alice, bob, erin = people[ALICE], people[BOB], people[ERIN]
    path = "/finance/plan.md"
    first = alice.tool("write", path=path, content="only finance: zebra-one")[1]
    # The folder opens to everyone and the file is rewritten.
    team.access("/finance", ["*"], ["@finance"])
    second = bob.tool("write", path=path, content="public text", version=first["version"])[1]
    seen = erin.tool("history", path=path)[1]["revisions"]
    assert [r["change"] for r in seen] == ["write"] and seen[0]["author"] == BOB
    everything = alice.tool("history", path=path)[1]["revisions"]
    assert [r["author"] for r in everything] == [ALICE, BOB]
    # Erin cannot restore, and cannot name, the revision written while it was private.
    private = everything[0]["revision"]
    assert erin.tool("restore", path=path, revision=private, version=second["version"])[0] in {
        "write_denied",
        "no_history",
    }
    team.access("/finance", ["*"], ["*"])
    refused = erin.tool("restore", path=path, revision=private, version=second["version"])
    assert refused[0] == "no_history"
    assert erin.tool("read", path=path)[1]["content"] == "public text"
    # Bob, who could read it all along, restores it.
    restored = bob.tool("restore", path=path, revision=private, version=second["version"])
    assert restored[0] == "ok" and bob.tool("read", path=path)[1]["content"].endswith("zebra-one")
    # A deleted file keeps its history for those who could read it, and only for them.
    team.access("/finance", ["@finance"], ["@finance"])
    alice.tool("delete", path=path, version=restored[1]["version"])
    assert alice.tool("history", path=path)[1]["revisions"][-1]["change"] == "delete"
    assert erin.tool("history", path=path)[0] == "no_history"
    assert erin.tool("history", path=path) == (
        "no_history",
        erin.tool("history", path="/finance/never-existed.md")[1],
    )
    assert_sound(team)


def test_a_group_emptied_by_removing_its_last_member_is_retired_like_a_deleted_one(
    team: Team, people: dict[str, Person]
) -> None:
    team.group("solo", DANA)
    team.access("/locked", ["@solo"], ["@solo"])
    assert people[DANA].tool("write", path="/locked/plan.md", content="old secret")[0] == "ok"
    assert team.admin.panel.delete(f"/api/users/{DANA}").status_code == 200
    # Nobody can be given the old name, so nobody inherits its folders or their history.
    assert code(team.group("solo", ERIN)) == "invalid_group"
    assert people[ERIN].tool("read", path="/locked/plan.md")[0] == "unavailable"
    assert people[ERIN].tool("history", path="/locked/plan.md")[0] == "no_history"
    # A group that still has members is untouched.
    team.admin.panel.delete(f"/api/users/{BOB}")
    assert team.admin.panel.get("/api/groups").json()["groups"]["finance"] == [ALICE]


def test_a_grant_typed_with_capital_letters_reaches_the_account(
    team: Team, people: dict[str, Person]
) -> None:
    assert team.access("/locked", ["Erin@Atlas.TEST"], ["Erin@Atlas.TEST"]).status_code == 200
    assert team.admin.tree("/locked").json()["read"] == [ERIN]
    assert sees(people[ERIN], "/locked/vault.md")
    # A file is not a folder: writing "inside" one is refused cleanly.
    inside = people[ERIN].tool("write", path="/locked/vault.md/x.md", content="x")
    assert inside[0] == "unavailable"
    assert_sound(team)


def test_a_link_left_unused_for_a_week_stops_working(team: Team, tmp_path: Path) -> None:
    invite = team.invite(ERIN)
    visitor = httpx.Client(base_url=team.base)
    with sqlite3.connect(tmp_path / "brainfold.db") as database:  # eight days go by
        database.execute("UPDATE users SET invited = invited - 8 * 24 * 3600")
    assert code(visitor.post("/api/accept", json={"invite": invite, "password": PASSWORD})) == (
        "invalid_invite"
    )
    # The administrator hands out a new one, which works.
    fresh = team.admin.panel.post(f"/api/users/{ERIN}/reset", json={}).json()["invite"]
    assert (
        visitor.post("/api/accept", json={"invite": fresh, "password": PASSWORD}).status_code == 200
    )


def test_a_password_reset_disconnects_every_harness_of_that_account_and_no_other(
    team: Team, people: dict[str, Person]
) -> None:
    link = team.admin.panel.post(f"/api/users/{ERIN}/reset", json={}).json()["invite"]
    assert people[ERIN].tool("list", path="/")[0] == "ok"  # nothing changes until it is used
    visitor = httpx.Client(base_url=team.base)
    assert (
        visitor.post("/api/accept", json={"invite": link, "password": "a-new-password"}).status_code
        == 200
    )
    assert people[ERIN].agent.get("/files/common/handbook.md").status_code == 401
    assert people[ERIN].tree().status_code == 401
    assert people[DANA].agent.get("/files/common/handbook.md").status_code == 200


def test_administration_refuses_people_who_are_not_there(
    team: Team, people: dict[str, Person]
) -> None:
    team.invite(PENDING := "pending@atlas.test")
    # Someone who has not accepted cannot be put in a group; the group stays as it was.
    assert code(team.group("finance", ALICE, PENDING)) == "invalid_group"
    assert code(team.group("finance", ALICE, "ghost@atlas.test")) == "invalid_group"
    assert team.admin.panel.get("/api/groups").json()["groups"]["finance"] == [ALICE, BOB]
    assert team.admin.panel.delete("/api/users/ghost@atlas.test").status_code == 404


def test_only_an_administrator_token_made_for_it_manages_access_from_a_harness(
    team: Team, people: dict[str, Person]
) -> None:
    admin, alice, erin = team.admin, people[ALICE], people[ERIN]
    calls: list[tuple[str, dict[str, Any]]] = [
        ("get_access", {"path": "/finance"}),
        ("set_access", {"path": "/finance", "read": ["*"], "write": ["*"]}),
        ("set_group", {"name": "finance", "members": [ERIN]}),
    ]
    # A member cannot ask for such a token, and neither kind of ordinary token manages.
    asked = erin.panel.post("/api/tokens", json={"name": "sneaky", "manage": True})
    assert code(asked) == "forbidden"
    for person in (erin, alice, admin):
        for name, arguments in calls:
            assert person.tool(name, **arguments)[0] == "forbidden"
    assert "Connect a harness" in admin.tool("get_access")[1]  # says how to get one
    assert not sees(erin, "/finance/budget.md")
    assert (team.root / "finance/.brainfold.toml").read_text("utf-8").count("@finance") == 2

    admin.connect("manager", manage=True)
    seen = admin.tool("get_access", path="/finance")[1]
    assert seen["read"] == ["@finance"] and seen["groups"]["finance"] == [ALICE, BOB]
    assert {"email": ERIN, "role": "member", "pending": False} in seen["members"]
    # Structure only, as in the panel: no content, and personal folders stay closed.
    assert {"path": "/finance/budget.md", "kind": "file"} in seen["entries"]
    assert admin.tool("read", path="/finance/budget.md")[0] == "unavailable"
    home = alice.tool("list")[1]["home"]
    assert admin.tool("get_access", path=home)[0] == "unavailable"
    assert admin.tool("set_access", path=home, read=["*"], write=None)[0] == "unavailable"
    assert admin.tool("set_access", path="/finance", read=["not a grant"], write=None)[0] == (
        "invalid_metadata"
    )

    # Granting and taking away both take effect at once, and the description survives.
    team.access("/finance", ["@finance"], ["@finance"], description="Money")
    assert admin.tool("set_access", path="/finance", read=["@finance", ERIN], write=None)[0] == "ok"
    assert sees(erin, "/finance/budget.md")
    after = admin.tool("get_access", path="/finance")[1]
    assert after["description"] == "Money" and after["write"] is None
    assert admin.tool("set_group", name="finance", members=[ALICE])[0] == "ok"
    assert not sees(people[BOB], "/finance/budget.md")
    assert admin.tool("set_group", name="finance", members=["ghost@atlas.test"])[0] == (
        "invalid_group"
    )
    log = admin.panel.get("/api/activity").json()["activity"]
    assert any(row["action"] == "edit_group" and row["ok"] for row in log)
    assert any(row["action"] == "edit_access" and not row["ok"] for row in log)

    # Revoking that one token ends it; the listing says which token manages.
    listed = admin.panel.get("/api/tokens").json()["tokens"]
    assert [token["manage"] for token in listed] == [False, True]
    admin.panel.delete(f"/api/tokens/{listed[1]['id']}")
    assert admin.tool("get_access")[0] == "unauthenticated"
    assert_sound(team)
