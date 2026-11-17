"""Regressions found by /qa on 2026-11-17.

Report: .gstack/qa-reports/run-20261117T131822Z/qa-report-brainfold-2026-11-17.md
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Any

import pytest
from team import serving

from brainfold import BrainfoldError
from brainfold.brain import Brain

EXAMPLE = Path(__file__).parent.parent / "examples" / "brain"
ALICE, PASSWORD = "alice@atlas.test", "a-long-password"
JSON = {"Accept": "application/json, text/event-stream"}


@pytest.fixture
def brain(tmp_path: Path) -> Brain:
    shutil.copytree(EXAMPLE, tmp_path / "brain")
    return Brain(tmp_path / "brain", lambda: {"costs": [ALICE]}, {ALICE: "alice-1a2b"}.get)


def code(call, *args, **kwargs) -> str:
    with pytest.raises(BrainfoldError) as error:
        call(*args, **kwargs)
    return error.value.code


# Regression: ISSUE-001 — every MCP request walked the caller's whole readable tree on the
# event loop to build the session instructions, and every write walked it again. On a
# 3,000-file brain a ping took 1.1 s and /api/health stalled for seconds under 8 agents.
# Found by /qa on 2026-11-17
# Report: .gstack/qa-reports/run-20261117T131822Z/qa-report-brainfold-2026-11-17.md
def test_only_a_session_start_walks_the_brain_and_never_on_the_event_loop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    walks: list[bool] = []
    original = Brain.skills

    def counted(self: Brain, who: str) -> Any:
        try:
            asyncio.get_running_loop()
            walks.append(True)  # on the event loop: everyone else waits
        except RuntimeError:
            walks.append(False)
        return original(self, who)

    monkeypatch.setattr(Brain, "skills", counted)
    shutil.copytree(EXAMPLE, tmp_path / "brain")
    with serving(tmp_path / "brain", tmp_path / "brainfold.db") as team:
        ana = team.join("ana@atlas.test")
        team.group("costs", ana)

        def rpc(method: str, params: dict[str, Any]) -> dict[str, Any]:
            body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
            return ana.agent.post("/mcp", json=body, headers=JSON).json()

        # The first tool call of a process lists the tools once to validate arguments.
        assert ana.tool("list", path="/")[0] == "ok"
        walks.clear()
        rpc("ping", {})
        assert ana.tool("list", path="/")[0] == "ok"
        assert ana.tool("read", path="/projects/costs/process.md")[0] == "ok"
        assert ana.tool("write", path="/projects/costs/note.md", content="x")[0] == "ok"
        assert ana.tool("append", path="/projects/costs/note.md", content="y")[0] == "ok"
        assert walks == []
        hello = {"protocolVersion": "2025-03-26", "capabilities": {}}
        started = rpc("initialize", hello | {"clientInfo": {"name": "qa", "version": "0"}})
        assert "analyze-costs-" in started["result"]["instructions"]
        skill = "---\nname: close\ndescription: Close the month\n---\n1. Do it.\n"
        answer = ana.tool("write", path="/projects/costs/close/SKILL.md", content=skill)
        assert answer[1]["skill"].startswith("close-")
        assert walks and not any(walks)
