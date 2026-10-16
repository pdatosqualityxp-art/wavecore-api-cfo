import os
import unittest
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.schemas.agent_cfo import AgentCFOPlan, AgentCFOQuery

os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")


class AgentCFOCustomerSalesTests(unittest.TestCase):
    def setUp(self) -> None:
        module = import_module("app.services.agent_cfo_service")
        for name, value in (("_TABLE_PAGE_SIZE", 10), ("_MAX_TABLE_ROWS", 50)):
            patcher = patch.object(module, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    @classmethod
    def setUpClass(cls) -> None:
        cls.service = import_module("app.services.agent_cfo_service")

    def test_customer_detail_question_is_forced_to_detail_tool(self) -> None:
        plan = AgentCFOPlan(queries=[AgentCFOQuery(source="sales")])

        routed = self.service._ensure_explicit_sources(
            "Dime las ventas del cliente Aroma de Gracia",
            plan,
        )

        self.assertEqual(len(routed.queries), 1)
        self.assertEqual(routed.queries[0].source, "customer_sales")
        self.assertEqual(routed.queries[0].search_term, "Aroma de Gracia")

    def test_customer_summary_question_uses_customer_filtered_aggregate(self) -> None:
        routed = self.service._ensure_explicit_sources(
            "¿Cuál es el total de ventas del cliente Aroma de Gracia?",
            AgentCFOPlan(queries=[AgentCFOQuery(source="sales")]),
        )

        self.assertEqual(len(routed.queries), 1)
        self.assertEqual(routed.queries[0].source, "sales")
        self.assertEqual(routed.queries[0].filter_by, "customer")
        self.assertEqual(routed.queries[0].group_by, "total")
        self.assertEqual(routed.queries[0].search_term, "Aroma de Gracia")

    def test_customer_name_in_question_can_include_date_period(self) -> None:
        routed = self.service._ensure_explicit_sources(
            "Dime las ventas del cliente Aroma de Gracia en 2025",
            AgentCFOPlan(queries=[]),
        )

        self.assertEqual(routed.queries[0].search_term, "Aroma de Gracia")
        self.assertEqual(routed.queries[0].source, "customer_sales")

    def test_customer_lookup_returns_explicit_not_found_result(self) -> None:
        query = AgentCFOQuery(
            source="customer_sales",
            search_term="Aroma de Gracia",
        )
        with patch.object(self.service, "_rpc_rows", return_value=[]) as rpc_rows:
            rows, complete = self.service._execute_customer_sales_query(query)

        self.assertTrue(complete)
        self.assertEqual(rows[0]["result_status"], "customer_not_found")
        self.assertEqual(rows[0]["requested_customer"], "Aroma de Gracia")
        rpc_rows.assert_called_once_with(
            "agent_cfo_find_customers",
            {"p_search": "Aroma de Gracia", "p_limit": 5},
        )

    def test_ambiguous_customer_names_do_not_mix_sales(self) -> None:
        query = AgentCFOQuery(source="customer_sales", search_term="Aroma")
        matches = [
            {
                "id_cliente": "C1",
                "nom_cliente": "Aroma de Gracia",
                "exact_match": False,
                "exact_match_count": 0,
                "match_count": 2,
            },
            {
                "id_cliente": "C2",
                "nom_cliente": "Aroma Gracia SL",
                "exact_match": False,
                "exact_match_count": 0,
                "match_count": 2,
            },
        ]

        with patch.object(self.service, "_rpc_rows", return_value=matches) as rpc_rows:
            rows, complete = self.service._execute_customer_sales_query(query)

        self.assertTrue(complete)
        self.assertEqual(rows[0]["result_status"], "ambiguous_customer")
        self.assertEqual(len(rows[0]["candidates"]), 2)
        self.assertEqual(rpc_rows.call_count, 1)

    def test_customer_sales_lookup_then_returns_individual_transactions(self) -> None:
        query = AgentCFOQuery(
            source="customer_sales",
            search_term="Aroma de Gracia",
            start_date="2025-01-01",
            end_date="2025-12-31",
        )
        match = {
            "id_cliente": "C1",
            "nom_cliente": "Aroma de Gracia",
            "exact_match": True,
            "exact_match_count": 1,
            "match_count": 1,
        }
        sales = [
            {
                "id_venta": "V1",
                "id_cliente": "C1",
                "nom_cliente": "Aroma de Gracia",
                "id_prod": "P1",
                "nom_prod": "Producto A",
                "unidades": 2,
                "total_venta": 120,
                "fecha_venta": "2025-06-01",
            }
        ]
        with patch.object(
            self.service,
            "_rpc_rows",
            side_effect=[[match], sales],
        ) as rpc_rows:
            rows, complete = self.service._execute_customer_sales_query(query)

        self.assertTrue(complete)
        self.assertEqual(rows, sales)
        self.assertEqual(rpc_rows.call_args_list[1].args[0], "agent_cfo_customer_sales")
        self.assertEqual(
            rpc_rows.call_args_list[1].args[1],
            {
                "p_customer_id": "C1",
                "p_start_date": "2025-01-01",
                "p_end_date": "2025-12-31",
                "p_limit": 10,
                "p_offset": 0,
            },
        )

    def test_customer_without_sales_is_distinguished_from_unknown_customer(self) -> None:
        query = AgentCFOQuery(source="customer_sales", search_term="Aroma de Gracia")
        match = {
            "id_cliente": "C1",
            "nom_cliente": "Aroma de Gracia",
            "exact_match": True,
            "exact_match_count": 1,
            "match_count": 1,
        }
        with patch.object(
            self.service,
            "_rpc_rows",
            side_effect=[[match], []],
        ):
            rows, complete = self.service._execute_customer_sales_query(query)

        self.assertTrue(complete)
        self.assertEqual(
            rows,
            [
                {
                    "result_status": "customer_has_no_sales",
                    "customer_id": "C1",
                    "customer_name": "Aroma de Gracia",
                }
            ],
        )

    def test_customer_sales_at_maximum_checks_for_an_additional_page(self) -> None:
        query = AgentCFOQuery(source="customer_sales", search_term="Aroma de Gracia")
        match = {
            "id_cliente": "C1",
            "nom_cliente": "Aroma de Gracia",
            "exact_match": True,
            "exact_match_count": 1,
            "match_count": 1,
        }
        pages = [
            [{"id_venta": f"V{offset + index}"} for index in range(10)]
            for offset in range(0, 50, 10)
        ]
        with patch.object(
            self.service,
            "_rpc_rows",
            side_effect=[[match], *pages, [{"id_venta": "V50"}]],
        ) as rpc_rows:
            rows, complete = self.service._execute_customer_sales_query(query)

        self.assertEqual(len(rows), 50)
        self.assertFalse(complete)
        self.assertEqual(rpc_rows.call_args_list[-1].args[1]["p_offset"], 50)
        self.assertEqual(rpc_rows.call_args_list[-1].args[1]["p_limit"], 1)

    def test_customer_sales_tool_is_wired_into_answer_evidence(self) -> None:
        plan = AgentCFOPlan(queries=[AgentCFOQuery(source="sales")])
        sales = [
            {
                "id_venta": "V1",
                "nom_cliente": "Aroma de Gracia",
                "nom_prod": "Producto A",
                "fecha_venta": "2025-06-01",
                "unidades": 2,
                "total_venta": 120,
            }
        ]
        supabase = MagicMock()
        model_response = SimpleNamespace(
            text="Aroma de Gracia compró Producto A.",
            usage_metadata=None,
        )

        with (
            patch.object(self.service, "_supabase", supabase),
            patch.object(
                self.service,
                "_plan_queries",
                side_effect=lambda question, _usage: (
                    self.service._ensure_explicit_sources(question, plan)
                ),
            ),
            patch.object(
                self.service,
                "_execute_customer_sales_query",
                return_value=(sales, True),
            ),
            patch.object(
                self.service._gemini.models,
                "generate_content",
                return_value=model_response,
            ) as generate_content,
        ):
            result = self.service._answer_question(
                "Dime las ventas del cliente Aroma de Gracia",
                None,
            )

        self.assertEqual(result.sources, [])
        self.assertIn(
            "ventas detalladas del cliente Aroma de Gracia",
            result.consulted_sources[0].reference,
        )
        evidence_prompt = generate_content.call_args.kwargs["contents"]
        self.assertIn('"nom_cliente": "Aroma de Gracia"', evidence_prompt)
        self.assertIn('"total_venta": 120', evidence_prompt)


if __name__ == "__main__":
    unittest.main()
