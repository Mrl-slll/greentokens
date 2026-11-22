import hashlib
import unittest
from datetime import timedelta
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.api.main import create_app
from core.database.models import Base, Organization, ProviderLogin, ProviderSession, User, now
from scripts.local_stack import seed


class ProviderAuthTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}, hide_parameters=True)
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)
        seed(self.sessions)
        self.client = TestClient(create_app(SimpleNamespace(max_bytes=65536, api_keys={}), self.sessions, SimpleNamespace()))
        self.credentials = {"username": "provider-one", "password": "test-only-password-123", "device_id": "device-0001"}

    def tearDown(self):
        self.client.close()
        self.engine.dispose()

    def signup(self, **changes):
        response = self.client.post("/v1/provider/auth/signup", json={**self.credentials, **changes})
        self.assertEqual(response.status_code, 201)
        return response

    def bearer(self, response):
        return {"Authorization": "Bearer " + response.json()["access_token"]}

    def heartbeat(self, headers, device="device-0001"):
        return self.client.post("/v1/provider/heartbeat", headers=headers, json={"device_id": device, "name": "Test PC",
            "status": "online", "capabilities": {"cpus": 2, "ram_gb": 4}})

    def test_signup_stores_hashes_and_only_provider_role(self):
        result = self.signup(username="  PROVIDER-one  ")
        self.assertEqual(result.headers["cache-control"], "no-store")
        self.assertEqual(result.json()["account"]["displayName"], "provider-one")
        with self.sessions() as db:
            login = db.get(ProviderLogin, "provider-one")
            self.assertTrue(login.password_hash.startswith("scrypt-v1$"))
            self.assertNotIn(self.credentials["password"], login.password_hash)
            self.assertEqual(db.get(User, login.user_id).role, "provider")
            session = db.scalar(select(ProviderSession))
            self.assertNotEqual(session.token_hash, result.json()["access_token"])
            self.assertEqual(session.token_hash, hashlib.sha256(result.json()["access_token"].encode()).hexdigest())
        self.assertEqual(self.heartbeat(self.bearer(result)).status_code, 200)
        self.assertEqual(self.client.get("/v1/workers", headers=self.bearer(result)).status_code, 403)
        self.assertEqual(self.client.post("/v1/jobs", headers=self.bearer(result), json={"template_id": "sum_numbers_v1",
            "parameters": {"values": [1]}, "idempotency_key": "forbidden"}).status_code, 403)

    def test_password_login_and_generic_failure(self):
        self.signup()
        good = self.client.post("/v1/provider/auth/login", json=self.credentials)
        self.assertEqual(good.status_code, 200)
        self.assertEqual(self.heartbeat(self.bearer(good)).status_code, 200)
        wrong = self.client.post("/v1/provider/auth/login", json={**self.credentials, "password": "wrong-password-123"})
        missing = self.client.post("/v1/provider/auth/login", json={**self.credentials, "username": "missing"})
        self.assertEqual(wrong.status_code, 401)
        self.assertEqual(wrong.json(), missing.json())

    def test_relogin_revokes_only_same_device_session(self):
        first = self.signup()
        second = self.client.post("/v1/provider/auth/login", json={**self.credentials, "device_id": "device-0002"})
        replacement = self.client.post("/v1/provider/auth/login", json=self.credentials)
        self.assertEqual(self.heartbeat(self.bearer(first)).status_code, 401)
        self.assertEqual(self.heartbeat(self.bearer(second), "device-0002").status_code, 200)
        self.assertEqual(self.heartbeat(self.bearer(replacement)).status_code, 200)

    def test_session_is_device_bound_and_other_accounts_cannot_claim_it(self):
        first = self.signup()
        self.assertEqual(self.heartbeat(self.bearer(first), "device-other").status_code, 403)
        self.assertEqual(self.heartbeat(self.bearer(first)).status_code, 200)
        other = self.signup(username="provider-two")
        self.assertEqual(self.heartbeat(self.bearer(other)).status_code, 403)

    def test_logout_and_expiry_reject_worker_requests(self):
        signed = self.signup()
        headers = self.bearer(signed)
        self.assertEqual(self.client.post("/v1/provider/auth/logout", headers=headers).status_code, 204)
        self.assertEqual(self.heartbeat(headers).status_code, 401)
        signed = self.client.post("/v1/provider/auth/login", json=self.credentials)
        with self.sessions.begin() as db:
            db.scalar(select(ProviderSession)).expires_at = now() - timedelta(seconds=1)
        self.assertEqual(self.heartbeat(self.bearer(signed)).status_code, 401)

    def test_refresh_rotates_session_and_keeps_device_binding(self):
        signed = self.signup()
        old = self.bearer(signed)
        refreshed = self.client.post("/v1/provider/auth/refresh", headers=old, json={"device_id": "device-0001"})
        self.assertEqual(refreshed.status_code, 200)
        self.assertEqual(refreshed.headers["cache-control"], "no-store")
        self.assertEqual(refreshed.json()["account"], {"displayName": "provider-one", "deviceId": "device-0001"})
        self.assertNotEqual(refreshed.json()["access_token"], signed.json()["access_token"])
        self.assertEqual(self.heartbeat(old).status_code, 401)
        self.assertEqual(self.heartbeat(self.bearer(refreshed)).status_code, 200)
        with self.sessions() as db:
            self.assertGreater(db.scalar(select(ProviderSession)).expires_at, now() + timedelta(days=29))
        new = self.bearer(refreshed)
        self.assertEqual(self.client.post("/v1/provider/auth/refresh", headers=new,
                                          json={"device_id": "device-other"}).status_code, 401)
        self.assertEqual(self.client.post("/v1/provider/auth/refresh", json={"device_id": "device-0001"}).status_code, 401)
        with self.sessions.begin() as db:
            db.scalar(select(ProviderSession)).expires_at = now() - timedelta(seconds=1)
        self.assertEqual(self.client.post("/v1/provider/auth/refresh", headers=new,
                                          json={"device_id": "device-0001"}).status_code, 401)

    def test_duplicate_signup_does_not_leave_extra_organizations(self):
        self.signup()
        with self.sessions() as db:
            before = db.scalar(select(func.count()).select_from(Organization))
        duplicate = self.client.post("/v1/provider/auth/signup", json=self.credentials)
        self.assertEqual(duplicate.status_code, 409)
        with self.sessions() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Organization)), before)

    def test_invalid_body_does_not_echo_password_and_no_role_escalation(self):
        for changes in ({"password": ""}, {"password": "x" * 1025}, {"role": "admin"}, {"username": "bad@name"}):
            response = self.client.post("/v1/provider/auth/signup", json={**self.credentials, **changes})
            self.assertEqual(response.status_code, 422)
            self.assertNotIn("password", response.text.lower())
        response = self.client.post("/v1/provider/auth/signup", content=b"x" * 4097, headers={"Content-Type": "application/json"})
        self.assertEqual(response.status_code, 413)

    def test_any_password_style_or_length_is_accepted(self):
        for i, password in enumerate(("a", "1234", "no rules at all!", "é" * 40)):
            body = {**self.credentials, "username": f"anypw{i}", "password": password}
            self.assertLess(self.client.post("/v1/provider/auth/signup", json=body).status_code, 300, password)

    def test_tunnel_cors_and_untrusted_origin(self):
        headers = {"Origin": "http://tauri.localhost", "CF-Connecting-IP": "203.0.113.2"}
        preflight = self.client.options("/v1/provider/auth/signup", headers={**headers,
            "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"})
        self.assertEqual(preflight.status_code, 200)
        self.assertEqual(preflight.headers["access-control-allow-origin"], headers["Origin"])
        response = self.client.post("/v1/provider/auth/signup", json=self.credentials, headers=headers)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.headers["access-control-allow-origin"], headers["Origin"])
        self.assertEqual(self.client.post("/v1/provider/auth/login", json=self.credentials,
            headers={"Origin": "https://evil.example"}).status_code, 403)

    def test_rate_limit_survives_application_restart(self):
        from core.api.provider_auth import throttle
        for _ in range(10):
            throttle(self.sessions, "auth:user:provider-one", 10)
        with TestClient(create_app(SimpleNamespace(max_bytes=65536, api_keys={}), self.sessions, SimpleNamespace())) as restarted:
            response = restarted.post("/v1/provider/auth/login", json=self.credentials)
            self.assertEqual(response.status_code, 429)
            self.assertIn("retry-after", response.headers)


if __name__ == "__main__":
    unittest.main()
