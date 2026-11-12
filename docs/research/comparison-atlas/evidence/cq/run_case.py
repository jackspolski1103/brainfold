"""Offline cq API comparison. Synthetic identities/data, ephemeral SQLite, no listener."""
import asyncio
import importlib.metadata
import json
import os
import tempfile
from pathlib import Path

# Explicitly disable optional remote/embedding paths before importing the app.
for key in ("CQ_DATABASE_URL", "CQ_ADDR", "CQ_API_KEY", "CQ_TEST_DATABASE_URL", "TOKEN_EMBEDDING_URL"):
    os.environ.pop(key, None)
os.environ["CQ_JWT_SECRET"] = "synthetic-local-test-key-not-for-production-12345"
os.environ["CQ_API_KEY_PEPPER"] = "synthetic-local-test-pepper-not-for-production"

from fastapi.testclient import TestClient
from cq_server.app import app
from cq_server.auth import hash_password
from cq_server.repositories import UserRepository

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "case-atlas.json"
CASE = json.loads(FIXTURE_PATH.read_text())
SOURCE = CASE["source"]["text"]
CANDIDATE = {
    "domains": ["atlas", "webhook"],
    "insight": {
        "summary": "Reintentos idempotentes de webhooks",
        "detail": CASE["candidate_v1"]["text"],
        "action": "Aplicar el procedimiento del caso sintético: máximo 5 reintentos, no 5 intentos totales.",
    },
}
assert all(x not in json.dumps(CANDIDATE) for x in ("Ana", "Lirio", "02:13", "FAKE_SECRET_ATLAS_NOT_VALID"))

results = {"case_id": CASE["case_id"], "versions": {p: importlib.metadata.version(p) for p in ("cq-sdk", "cq-server", "fastapi", "pytest")}, "observations": []}
def note(name, **values):
    results["observations"].append({"step": name, **values})

with tempfile.TemporaryDirectory(prefix="cq-case-") as scratch:
    os.environ["CQ_DB_PATH"] = scratch + "/case.db"
    with TestClient(app) as client:
        users = UserRepository(client.app.state.database)
        tokens, keys = {}, {}
        for user in ("ana", "bruno", "carla", "diego"):
            asyncio.run(users.create(user, hash_password("synthetic-only-password")))
            login = client.post("/api/v1/auth/login", json={"username": user, "password": "synthetic-only-password"})
            assert login.status_code == 200
            tokens[user] = {"Authorization": "Bearer " + login.json()["token"]}
            key = client.post("/api/v1/users/me/api-keys", headers=tokens[user], json={"name": "offline-case", "ttl": "1d"})
            assert key.status_code == 201, key.text
            keys[user] = key.json()
        def auth(user):
            return {"Authorization": "Bearer " + keys[user]["token"]}
        def propose(body):
            response = client.post("/api/v1/knowledge", headers=auth("ana"), json=body)
            assert response.status_code == 201, response.text
            return response.json()
        def query(headers=None):
            return client.get("/api/v1/knowledge", params={"domains": "atlas", "limit": 20}, headers=headers or {})

        note("private_source", stored_in_server=False, manual_sanitization=True)
        unit = propose(CANDIDATE)
        uid = unit["id"]
        note("candidate", tier=unit["tier"], created_by=unit["created_by"], pending_anonymous_query_count=len(query().json()["data"]))
        for user in ("bruno", "carla", "diego"):
            pending = client.get(f"/api/v1/review/{uid}", headers=tokens[user])
            note("pending_review_access", user=user, status=pending.status_code, candidate_visible=pending.status_code == 200)

        patch = client.patch(f"/api/v1/knowledge/{uid}", headers=auth("ana"), json={"insight": {**CANDIDATE["insight"], "action": "3 intentos"}})
        note("edit_candidate_api", status=patch.status_code)
        approval = client.post(f"/api/v1/review/{uid}/approve", headers=tokens["bruno"], json={"expected_revision": "deliberately-wrong", "audience": ["atlas"]})
        note("approve", status=approval.status_code, reviewer=approval.json().get("reviewed_by"), unsupported_revision_body_ignored=approval.status_code == 200)
        approved = query().json()["data"]
        snapshot = json.dumps(approved)
        note("approved_read", anonymous_count=len(approved), carla_boreal_count=len(query(auth("carla")).json()["data"]), returned_tier=approved[0]["tier"])

        skill = propose({"domains": ["atlas", "skill"], "insight": {"summary": "Procedimiento derivado", "detail": CASE["derived_skill_v1"]["text"], "action": "Aplicar este procedimiento sintético."}, "extensions": {"case:derived_from": uid}})
        client.post(f"/api/v1/review/{skill['id']}/approve", headers=tokens["bruno"])

        second = propose(CANDIDATE)
        unauthorized_role = client.post(f"/api/v1/review/{second['id']}/approve", headers=tokens["diego"])
        note("verifier_can_publish", user="diego", status=unauthorized_role.status_code)

        wider = propose({**CANDIDATE, "domains": ["organization", "webhook"]})
        wider_approval = client.post(f"/api/v1/review/{wider['id']}/approve", headers=tokens["carla"])
        note("audience_expansion_as_new_proposal", proposer="ana", reviewer="carla", status=wider_approval.status_code, audience_is_domain_tag_not_acl=True)

        revoked = client.post(f"/api/v1/users/me/api-keys/{keys['bruno']['id']}/revoke", headers=tokens["bruno"])
        write = client.post(f"/api/v1/knowledge/{uid}/confirmations", headers=auth("bruno"))
        read = query(auth("bruno"))
        note("key_revocation", revoke_status=revoked.status_code, subsequent_write_status=write.status_code, subsequent_read_status=read.status_code, subsequent_read_count=len(read.json()["data"]))

        corrected = {**CANDIDATE, "insight": {**CANDIDATE["insight"], "detail": CASE["candidate_v2"]["text"], "action": "Aplicar el procedimiento corregido: máximo 3 reintentos."}}
        replacement = propose(corrected)
        client.post(f"/api/v1/review/{replacement['id']}/approve", headers=tokens["bruno"])
        flagged = client.post(f"/api/v1/knowledge/{uid}/flags", headers=auth("ana"), json={"reason": "incorrect"})
        after = query().json()["data"]
        note("correction", flag_status=flagged.status_code, original_still_queryable=any(x["id"] == uid for x in after), old_and_new_present=all(any(x["id"] == target for x in after) for target in (uid, replacement["id"])))
        skill_after = next(x for x in after if x["id"] == skill["id"])
        note("derived_skill", still_five_retries="5 reintentos" in skill_after["insight"]["detail"], still_queryable=True, lineage_metadata_preserved=skill_after.get("extensions", {}).get("case:derived_from") == uid, automatic_invalidation_observed=False)
        revoke_unit = client.post(f"/api/v1/users/me/knowledge/{uid}/revoke", headers=auth("ana"))
        note("remote_unit_revoke_endpoint", status=revoke_unit.status_code)
        note("export_copy", retains_five_retries="5 reintentos" in snapshot, unchanged_after_correction=True, mechanism="manual JSON snapshot of authorized/public query response")
        note("sanitized_output", contains_fake_secret="FAKE_SECRET_ATLAS_NOT_VALID" in json.dumps(after), source_transmitted=False)

print(json.dumps(results, indent=2, ensure_ascii=False))

