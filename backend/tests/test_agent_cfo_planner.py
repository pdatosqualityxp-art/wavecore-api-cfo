import os
import unittest
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")


class AgentCFOPlannerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.service = import_module("app.services.agent_cfo_service")

    def test_invalid_plan_is_retried_with_validation_feedback(self) -> None:
        responses = [
            SimpleNamespace(
                text='{"queries":[{"source":"stock"}]}',
                usage_metadata=None,
            ),
            SimpleNamespace(
                text='{"queries":[{"source":"stock","item_type":"product"}]}',
                usage_metadata=None,
            ),
        ]
        usage = {"prompt_tokens": 0, "response_tokens": 0, "total_tokens": 0}
        with patch.object(
            self.service._gemini.models,
            "generate_content",
            side_effect=responses,
        ) as generate_content:
            plan = self.service._plan_queries("¿Qué productos hay en stock?", usage)

        self.assertEqual(len(plan.queries), 1)
        self.assertEqual(plan.queries[0].item_type, "product")
        self.assertEqual(generate_content.call_count, 2)
        retry_contents = generate_content.call_args.kwargs["contents"]
        self.assertIn("Pregunta original:", retry_contents)
        self.assertIn("item_type", retry_contents)

    def test_invalid_plan_after_retry_raises_service_error(self) -> None:
        invalid_response = SimpleNamespace(
            text='{"queries":[{"source":"stock"}]}',
            usage_metadata=None,
        )
        usage = {"prompt_tokens": 0, "response_tokens": 0, "total_tokens": 0}
        with (
            patch.object(
                self.service._gemini.models,
                "generate_content",
                return_value=invalid_response,
            ) as generate_content,
            self.assertRaises(self.service.AgentCFOServiceError),
        ):
            self.service._plan_queries("¿Qué hay en stock?", usage)

        self.assertEqual(generate_content.call_count, 2)

    def test_budget_and_sales_question_always_queries_both_sources(self) -> None:
        response = SimpleNamespace(
            text='{"queries":[{"source":"sales","group_by":"total"}]}',
            usage_metadata=None,
        )
        usage = {"prompt_tokens": 0, "response_tokens": 0, "total_tokens": 0}
        with patch.object(
            self.service._gemini.models,
            "generate_content",
            return_value=response,
        ):
            plan = self.service._plan_queries(
                "Según el presupuesto y las ventas, ¿qué conclusión tenemos?",
                usage,
            )

        self.assertEqual(
            [query.source for query in plan.queries],
            ["documents", "sales"],
        )
        self.assertEqual(plan.queries[0].document_title, "presupuesto")


if __name__ == "__main__":
    unittest.main()
