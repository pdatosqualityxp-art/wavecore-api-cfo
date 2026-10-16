import os
import unittest
from importlib import import_module
from types import SimpleNamespace
from uuid import UUID
from unittest.mock import MagicMock, patch

from app.schemas.agent_cfo import AgentCFOPlan, AgentCFOQuery

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
        conversation_id = UUID("490af1b6-7b43-4b09-a941-a528ee5bf7bf")
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
                conversation_id,
            )

        expected_answer = (
            "Las ventas fueron 100 €.\n\nModelo utilizado: gemini-3.5-flash-lite"
        )
        self.assertEqual(result.answer, expected_answer)
        self.assertEqual(result.model, "gemini-3.5-flash-lite")
        self.assertEqual(result.conversation_id, conversation_id)
        self.assertEqual(self.supabase.table.call_count, 2)
        self.supabase.table.assert_called_with("chat_logs")
        logged = self.table.insert.call_args.args[0]
        self.assertEqual(
            logged,
            {
                "conversation_id": str(conversation_id),
                "model_used": "gemini-3.5-flash-lite",
                "prompt": "¿Cuánto vendimos?",
                "reply": expected_answer,
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

    def test_conversation_history_uses_recent_successful_turns_in_order(self) -> None:
        conversation_id = UUID("490af1b6-7b43-4b09-a941-a528ee5bf7bf")
        rows = [
            {"prompt": "Pregunta reciente", "reply": "Respuesta reciente"},
            {
                "prompt": "Pregunta fallida",
                "reply": "La consulta no pudo completarse.",
            },
            {"prompt": "Pregunta anterior", "reply": "Respuesta anterior"},
        ]
        (
            self.table.select.return_value.eq.return_value.eq.return_value
            .order.return_value.order.return_value.limit.return_value
            .execute.return_value
        ).data = rows

        with patch.object(self.service, "_supabase", self.supabase):
            history = self.service._load_conversation_history(conversation_id)

        self.assertEqual(
            history,
            [
                {"user": "Pregunta anterior", "assistant": "Respuesta anterior"},
                {"user": "Pregunta reciente", "assistant": "Respuesta reciente"},
            ],
        )
        select = self.table.select.return_value
        select.eq.assert_called_once_with("conversation_id", str(conversation_id))
        select.eq.return_value.eq.assert_called_once_with("api", "2 FastAPI")
        select.eq.return_value.eq.return_value.order.assert_called_once_with(
            "created_at",
            desc=True,
        )

    def test_response_reports_consulted_sources_even_when_queries_return_no_rows(self) -> None:
        plan = AgentCFOPlan(
            queries=[
                AgentCFOQuery(
                    source="documents",
                    document_title="presupuesto",
                ),
                AgentCFOQuery(source="sales"),
            ]
        )
        model_response = SimpleNamespace(
            text="No encontré evidencia suficiente.",
            usage_metadata=None,
        )
        with (
            patch.object(self.service, "_supabase", self.supabase),
            patch.object(self.service, "_plan_queries", return_value=plan),
            patch.object(self.service, "_execute_query", return_value=[]),
            patch.object(
                self.service._gemini.models,
                "generate_content",
                return_value=model_response,
            ),
        ):
            result = self.service._answer_question(
                "Según el presupuesto y ventas",
                None,
            )

        self.assertEqual(
            [source.model_dump() for source in result.consulted_sources],
            [
                {"type": "pdf", "reference": "presupuesto"},
                {
                    "type": "table",
                    "reference": "ventas (informe agregado: productos y clientes)",
                },
            ],
        )
        self.assertEqual(result.sources, [])

    def test_consulted_sources_include_each_document_once_without_page_numbers(self) -> None:
        title = "Contrato de ventas Aroma de Gracia"
        plan = AgentCFOPlan(
            queries=[
                AgentCFOQuery(source="documents", document_title=title),
                AgentCFOQuery(source="stock", item_type="product"),
                AgentCFOQuery(source="sales"),
            ]
        )
        chunks = [
            {"titulo": title, "page_number": 3, "chunk_text": "x"},
            {"titulo": title, "page_number": 1, "chunk_text": "y"},
            {"titulo": title, "page_number": 3, "chunk_text": "z"},
        ]
        model_response = SimpleNamespace(
            text="Respuesta con evidencias.",
            usage_metadata=None,
        )
        with (
            patch.object(self.service, "_supabase", self.supabase),
            patch.object(self.service, "_load_conversation_history", return_value=[]),
            patch.object(self.service, "_plan_queries", return_value=plan),
            patch.object(
                self.service,
                "_execute_stock_query",
                return_value=([], True),
            ),
            patch.object(
                self.service,
                "_execute_query",
                side_effect=[chunks, []],
            ),
            patch.object(
                self.service._gemini.models,
                "generate_content",
                return_value=model_response,
            ),
        ):
            result = self.service._answer_question("Analiza el contrato", None)

        self.assertEqual(
            [source.model_dump() for source in result.consulted_sources],
            [
                {"type": "pdf", "reference": title},
                {"type": "table", "reference": "stock_prod, productos y almacen"},
                {
                    "type": "table",
                    "reference": "ventas (informe agregado: productos y clientes)",
                },
                {"type": "document", "reference": title},
            ],
        )
        self.assertEqual(len(result.sources), 3)

    def test_previous_turns_are_passed_to_planner_and_answer_model(self) -> None:
        conversation_id = UUID("490af1b6-7b43-4b09-a941-a528ee5bf7bf")
        history = [
            {
                "user": "¿Qué sabes de Nova1?",
                "assistant": "El producto Nova1 (id: PROD0001) es una máquina espresso.",
            }
        ]
        plan = AgentCFOPlan(
            queries=[AgentCFOQuery(source="stock", item_type="product")]
        )
        model_response = SimpleNamespace(
            text="Sí, tiene ventas.",
            usage_metadata=None,
        )
        with (
            patch.object(self.service, "_supabase", self.supabase),
            patch.object(
                self.service,
                "_load_conversation_history",
                return_value=history,
            ),
            patch.object(
                self.service,
                "_plan_queries",
                return_value=plan,
            ) as plan_queries,
            patch.object(
                self.service,
                "_rpc_rows",
                return_value=[
                    {"id_prod": "PROD0001", "nom_prod": "Nova1"},
                ],
            ) as rpc_rows,
            patch.object(
                self.service._gemini.models,
                "generate_content",
                return_value=model_response,
            ) as generate_content,
        ):
            result = self.service._answer_question(
                "¿Y se vende mucho?",
                None,
                conversation_id,
            )

        self.assertEqual(plan_queries.call_args.args[0], "¿Y se vende mucho?")
        self.assertEqual(plan_queries.call_args.args[2], history)
        self.assertEqual(
            rpc_rows.call_args_list[0].args,
            (
                "agent_cfo_products_catalog",
                {"p_search": "PROD0001", "p_limit": 10, "p_offset": 0},
            ),
        )
        self.assertEqual(
            rpc_rows.call_args_list[1].args[1]["p_search"],
            "Nova1",
        )
        answer_contents = generate_content.call_args.kwargs["contents"]
        self.assertIn("Nova1", answer_contents)
        self.assertIn("no es evidencia", answer_contents)
        self.assertEqual(result.conversation_id, conversation_id)

    def test_stock_coverage_follows_all_product_ids_in_recent_answer(self) -> None:
        history = [
            {
                "user": "atlas",
                "assistant": (
                    "Atlas2 ID PROD0003 y Atlas3 ID PROD0004."
                ),
            }
        ]
        plan = self.service._ensure_explicit_sources(
            "¿Tenemos stock suficiente para las ventas habituales de este producto?",
            AgentCFOPlan(
                queries=[
                    AgentCFOQuery(
                        source="stock_coverage",
                        search_term="Atlas",
                    )
                ]
            ),
            history,
        )

        self.assertEqual(
            [
                (query.source, query.search_term)
                for query in plan.queries
            ],
            [
                ("stock_coverage", "PROD0003"),
                ("stock_coverage", "PROD0004"),
            ],
        )

    def test_stock_coverage_answer_uses_calculated_metrics_and_citations(self) -> None:
        answer = self.service._stock_coverage_answer(
            [
                {
                    "source_id": "S1",
                    "details": {
                        "product_id": "PROD0003",
                        "product_name": "Atlas2",
                        "current_stock_units": "69",
                        "transactions_last_6_months": "28",
                        "units_sold_last_6_months": "28",
                        "average_monthly_units": "4.67",
                        "coverage_months": "14.79",
                        "stock_covers_one_month": True,
                        "period_start": "2026-04-01",
                        "period_end": "2026-09-30",
                    },
                }
            ]
        )

        self.assertIn("Atlas2 (PROD0003)", answer)
        self.assertIn("promedio de 4.67 unidades al mes", answer)
        self.assertIn("14.79 meses de cobertura", answer)
        self.assertIn("sí alcanza para cubrir un mes", answer)
        self.assertIn("[S1]", answer)

    def test_stock_coverage_without_recent_sales_does_not_claim_zero_demand(self) -> None:
        answer = self.service._stock_coverage_answer(
            [
                {
                    "source_id": "S1",
                    "details": {
                        "product_id": "PROD0003",
                        "product_name": "Atlas2",
                        "transactions_last_6_months": "0",
                        "period_start": "2026-04-01",
                        "period_end": "2026-09-30",
                    },
                }
            ]
        )

        self.assertIn("no hay unidades vendidas", answer)
        self.assertNotIn("demanda cero", answer)
        self.assertIn("[S1]", answer)

    def test_stock_coverage_question_returns_deterministic_comparison_for_context_products(
        self,
    ) -> None:
        conversation_id = UUID("490af1b6-7b43-4b09-a941-a528ee5bf7bf")
        history = [
            {
                "user": "atlas",
                "assistant": (
                    "Atlas2 ID PROD0003 y Atlas3 ID PROD0004."
                ),
            }
        ]
        coverage_rows = [
            {
                "product_id": "PROD0003",
                "product_name": "Atlas2",
                "current_stock_units": 69,
                "transactions_last_6_months": 28,
                "units_sold_last_6_months": 28,
                "average_monthly_units": "4.67",
                "coverage_months": "14.79",
                "stock_covers_one_month": True,
                "period_start": "2026-04-01",
                "period_end": "2026-09-30",
            },
            {
                "product_id": "PROD0004",
                "product_name": "Atlas3",
                "current_stock_units": 42,
                "transactions_last_6_months": 23,
                "units_sold_last_6_months": 23,
                "average_monthly_units": "3.83",
                "coverage_months": "10.96",
                "stock_covers_one_month": True,
                "period_start": "2026-04-01",
                "period_end": "2026-09-30",
            },
        ]
        with (
            patch.object(self.service, "_supabase", self.supabase),
            patch.object(
                self.service,
                "_load_conversation_history",
                return_value=history,
            ),
            patch.object(
                self.service,
                "_plan_queries",
                side_effect=lambda question, usage, turns: self.service
                ._ensure_explicit_sources(
                    question,
                    AgentCFOPlan(queries=[]),
                    turns,
                ),
            ),
            patch.object(
                self.service,
                "_rpc_rows",
                side_effect=[coverage_rows[0:1], coverage_rows[1:2]],
            ) as rpc_rows,
            patch.object(
                self.service._gemini.models,
                "generate_content",
                side_effect=AssertionError("Coverage response must be deterministic"),
            ),
        ):
            result = self.service._answer_question(
                "¿Tenemos stock suficiente para las ventas habituales de este producto?",
                None,
                conversation_id,
            )

        self.assertIn("Atlas2 (PROD0003)", result.answer)
        self.assertIn("Atlas3 (PROD0004)", result.answer)
        self.assertIn("sí alcanza para cubrir un mes", result.answer)
        self.assertEqual(
            [source.reference for source in result.consulted_sources],
            [
                "stock_prod y ventas (cobertura frente al promedio mensual de los últimos 6 meses completos)"
            ],
        )
        self.assertEqual(
            [
                call.args[1]["p_search"]
                for call in rpc_rows.call_args_list
            ],
            ["PROD0003", "PROD0004"],
        )

    def test_forecast_stock_question_does_not_use_historical_sales_as_forecast(self) -> None:
        conversation_id = UUID("490af1b6-7b43-4b09-a941-a528ee5bf7bf")
        with (
            patch.object(self.service, "_supabase", self.supabase),
            patch.object(self.service, "_load_conversation_history", return_value=[]),
            patch.object(
                self.service,
                "_plan_queries",
                side_effect=AssertionError("Forecast question should not be planned"),
            ),
            patch.object(
                self.service._gemini.models,
                "generate_content",
                side_effect=AssertionError("Forecast answer should be deterministic"),
            ),
        ):
            result = self.service._answer_question(
                "¿Tenemos stock suficiente para las ventas previstas?",
                None,
                conversation_id,
            )

        self.assertIn("no dispone de una previsión futura", result.answer)
        self.assertEqual(result.consulted_sources, [])
        self.assertEqual(result.conversation_id, conversation_id)


if __name__ == "__main__":
    unittest.main()
