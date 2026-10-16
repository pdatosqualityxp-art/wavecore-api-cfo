import os
import unittest
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")

from fastapi.security import HTTPAuthorizationCredentials  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from supabase_auth.errors import AuthApiError  # noqa: E402


def _user_response(is_anonymous: bool) -> SimpleNamespace:
    return SimpleNamespace(user=SimpleNamespace(id="user-1", is_anonymous=is_anonymous))


class AuthDependencyTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.auth = import_module("app.core.auth")

    def _credentials(self, token: str = "token") -> HTTPAuthorizationCredentials:
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    async def test_missing_token_is_rejected(self) -> None:
        with self.assertRaises(Exception) as context:
            await self.auth.get_current_user(None)
        self.assertEqual(context.exception.status_code, 401)

    async def test_invalid_token_is_rejected(self) -> None:
        auth_client = MagicMock()
        auth_client.get_user.side_effect = AuthApiError("invalid JWT", 401, "bad_jwt")
        with patch.object(self.auth, "_supabase_auth", auth_client):
            with self.assertRaises(Exception) as context:
                await self.auth.get_current_user(self._credentials())
        self.assertEqual(context.exception.status_code, 401)

    async def test_auth_service_failure_returns_503(self) -> None:
        auth_client = MagicMock()
        auth_client.get_user.side_effect = RuntimeError("network down")
        with patch.object(self.auth, "_supabase_auth", auth_client):
            with self.assertRaises(Exception) as context:
                await self.auth.get_current_user(self._credentials())
        self.assertEqual(context.exception.status_code, 503)

    async def test_valid_token_returns_user_and_guests_are_allowed(self) -> None:
        auth_client = MagicMock()
        auth_client.get_user.return_value = _user_response(is_anonymous=True)
        with patch.object(self.auth, "_supabase_auth", auth_client):
            user = await self.auth.get_current_user(self._credentials("abc"))
        self.assertEqual(user.id, "user-1")
        auth_client.get_user.assert_called_once_with("abc")

    async def test_registered_user_requirement_rejects_guests(self) -> None:
        guest = _user_response(is_anonymous=True).user
        registered = _user_response(is_anonymous=False).user
        with self.assertRaises(Exception) as context:
            await self.auth.get_registered_user(guest)
        self.assertEqual(context.exception.status_code, 403)
        self.assertIs(await self.auth.get_registered_user(registered), registered)


class RouterProtectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.auth = import_module("app.core.auth")
        cls.main = import_module("main")
        cls.client = TestClient(cls.main.app)

    def test_agent_requires_bearer(self) -> None:
        response = self.client.post("/api/agent_cfo", json={"question": "hola"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers["www-authenticate"], "Bearer")

    def test_ingest_requires_bearer(self) -> None:
        response = self.client.post("/api/documents/ingest")
        self.assertEqual(response.status_code, 401)

    def test_ingest_rejects_guest_sessions(self) -> None:
        auth_client = MagicMock()
        auth_client.get_user.return_value = _user_response(is_anonymous=True)
        with patch.object(self.auth, "_supabase_auth", auth_client):
            response = self.client.post(
                "/api/documents/ingest",
                headers={"Authorization": "Bearer guest-token"},
            )
        self.assertEqual(response.status_code, 403)

    def test_agent_accepts_guest_sessions(self) -> None:
        auth_client = MagicMock()
        auth_client.get_user.return_value = _user_response(is_anonymous=True)
        router_module = import_module("app.routers.agent_cfo")
        with (
            patch.object(self.auth, "_supabase_auth", auth_client),
            patch.object(
                router_module,
                "answer_question",
                AsyncMock(
                    return_value={
                        "answer": "ok",
                        "model": "m",
                        "conversation_id": "490af1b6-7b43-4b09-a941-a528ee5bf7bf",
                        "sources": [],
                        "consulted_sources": [],
                    }
                ),
            ),
        ):
            response = self.client.post(
                "/api/agent_cfo",
                json={"question": "hola"},
                headers={"Authorization": "Bearer guest-token"},
            )
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
