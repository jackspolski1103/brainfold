"""Complementary local-only CQ SDK test with the same fixture, no remote calls."""
import json
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
repo = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(repo / "sdk/python/src"))
os.environ.pop("CQ_ADDR", None)
os.environ.pop("CQ_API_KEY", None)
from cq.client import Client
from cq.stores.memory import InMemoryStore

case = json.loads((root.parents[1] / "case-atlas.json").read_text())
with Client(store=InMemoryStore()) as client:
    unit = client.propose("Reintentos idempotentes", case["candidate_v1"]["text"], "Aplicar procedimiento sintético.", ["atlas"], created_by="ana")
    before = len(client.query(["atlas"]).units)
    copied = unit.model_dump_json()
    client.revoke(unit.id)
    after = len(client.query(["atlas"]).units)
    print(json.dumps({"sdk_source": "pinned repository sdk/python/src", "tier": unit.tier, "local_query_without_review": before, "after_local_revoke": after, "copy_still_has_five_retries": "5 reintentos" in copied, "warning": "single-process local store; not a human authorization test"}, indent=2))

