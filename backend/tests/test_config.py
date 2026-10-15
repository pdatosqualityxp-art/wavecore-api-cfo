import os
import unittest
from unittest.mock import patch

from app.core.config import Settings


class SettingsModelTests(unittest.TestCase):
    def test_gemini_models_use_defaults_when_not_configured(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings(
                _env_file=None,
                supabase_url="http://localhost:54321",
                supabase_service_role_key="test-service-role-key",
                gemini_api_key="test-gemini-key",
            )

        self.assertEqual(settings.gemini_agent_model, "gemini-3.5-flash-lite")
        self.assertEqual(settings.gemini_embedding_model, "gemini-embedding-001")

    def test_gemini_models_can_be_overridden_by_environment(self) -> None:
        with patch.dict(
            os.environ,
            {
                "GEMINI_AGENT_MODEL": "custom-agent-model",
                "GEMINI_EMBEDDING_MODEL": "custom-embedding-model",
            },
            clear=True,
        ):
            settings = Settings(
                _env_file=None,
                supabase_url="http://localhost:54321",
                supabase_service_role_key="test-service-role-key",
                gemini_api_key="test-gemini-key",
            )

        self.assertEqual(settings.gemini_agent_model, "custom-agent-model")
        self.assertEqual(settings.gemini_embedding_model, "custom-embedding-model")


if __name__ == "__main__":
    unittest.main()
