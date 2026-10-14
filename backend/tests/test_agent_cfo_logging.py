import os
import unittest
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.schemas.agent_cfo import AgentCFOPlan

os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")


class AgentCFOLoggingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.agent_cfo_service = import_module("app.services.agent_cfo_service")

    def setUp(self) -> None:
        self.table = MagicMock()
        self.supabase = MagicMock()
        self.supabase.table.return_value = self.table
        self.service = self.agent_cfo_service

    def test_successful_consultation_is_logged_with_tokens_and_client_ip(self) -> None:
        usage = SimpleNamespace(
            prompt_token_count=12,
            candidates_token_count=4,
            total_token_count=16,
        )
        model_response = SimpleNamespace(
            text="Las ventas fueron 100 €.",
            usage_metadata=usage,
        )
        with (
            patch.object(self.service, "_supabase", self.supabase),
            patch.object(
                self.service,
                "_plan_queries",
                return_value=AgentCFOPlan(queries=[]),
            ),
            patch.object(
                self.service._gemini.models,
                "generate_content",
                return_value=model_response,
            ),
        ):
            result = self.service._answer_question(
                "¿Cuánto vendimos?",
                "203.0.113.7",
            )

        self.assertEqual(result.answer, "Las ventas fueron 100 €.")
        self.supabase.table.assert_called_once_with("chat_logs")
        logged = self.table.insert.call_args.args[0]
        self.assertEqual(
            logged,
            {
                "model_used": "gemini-3.1-flash-lite",
                "prompt": "¿Cuánto vendimos?",
                "reply": "Las ventas fueron 100 €.",
                "prompt_tokens": 12,
                "response_tokens": 4,
                "total_tokens": 16,
                "client_ip": "203.0.113.7",
                "api": "2 FastAPI",
            },
        )
        self.table.insert.return_value.execute.assert_called_once_with()

    def test_failed_consultation_is_logged_before_error_is_raised(self) -> None:
        with (
            patch.object(self.service, "_supabase", self.supabase),
            patch.object(
                self.service,
                "_plan_queries",
                side_effect=self.service.AgentCFOServiceError("Planner failed"),
            ),
        ):
            with self.assertRaises(self.service.AgentCFOServiceError):
                self.service._answer_question("Pregunta fallida", None)

        logged = self.table.insert.call_args.args[0]
        self.assertEqual(logged["prompt"], "Pregunta fallida")
        self.assertEqual(logged["reply"], "La consulta no pudo completarse.")
        self.assertEqual(logged["api"], "2 FastAPI")


if __name__ == "__main__":
    unittest.main()
