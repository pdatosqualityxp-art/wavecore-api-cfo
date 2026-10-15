import os
import unittest
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.schemas.agent_cfo import AgentCFOPlan, AgentCFOQuery

os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")


class AgentCFOStockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.service = import_module("app.services.agent_cfo_service")

    def test_stock_query_retrieves_all_pages_when_under_maximum(self) -> None:
        query = AgentCFOQuery(source="stock", item_type="product")
        first_page = [{"item_name": f"Producto {index}"} for index in range(10)]
        second_page = [{"item_name": f"Producto {index}"} for index in range(10, 12)]

        with patch.object(
            self.service,
            "_rpc_rows",
            side_effect=[first_page, second_page],
        ) as rpc_rows:
            rows, complete = self.service._execute_stock_query(query)

        self.assertEqual(rows, first_page + second_page)
        self.assertTrue(complete)
        self.assertEqual(
            [call.args[1]["p_offset"] for call in rpc_rows.call_args_list],
            [0, 10],
        )

    def test_stock_query_marks_results_incomplete_when_more_than_maximum(self) -> None:
        query = AgentCFOQuery(source="stock", item_type="product")
        pages = [
            [{"item_name": f"Producto {offset + index}"} for index in range(10)]
            for offset in range(0, self.service._MAX_STOCK_ROWS, 10)
        ]
        extra_row = [{"item_name": "Producto adicional"}]

        with patch.object(
            self.service,
            "_rpc_rows",
            side_effect=[*pages, extra_row],
        ) as rpc_rows:
            rows, complete = self.service._execute_stock_query(query)

        self.assertEqual(len(rows), self.service._MAX_STOCK_ROWS)
        self.assertFalse(complete)
        self.assertEqual(
            rpc_rows.call_args_list[-1].args[1]["p_offset"],
            self.service._MAX_STOCK_ROWS,
        )
        self.assertEqual(rpc_rows.call_args_list[-1].args[1]["p_limit"], 1)

    def test_stock_query_is_complete_at_exact_maximum_when_no_more_rows_exist(self) -> None:
        query = AgentCFOQuery(source="stock", item_type="product")
        pages = [
            [{"item_name": f"Producto {offset + index}"} for index in range(10)]
            for offset in range(0, self.service._MAX_STOCK_ROWS, 10)
        ]

        with patch.object(
            self.service,
            "_rpc_rows",
            side_effect=[*pages, []],
        ) as rpc_rows:
            rows, complete = self.service._execute_stock_query(query)

        self.assertEqual(len(rows), self.service._MAX_STOCK_ROWS)
        self.assertTrue(complete)
        self.assertEqual(
            rpc_rows.call_args_list[-1].args[1]["p_offset"],
            self.service._MAX_STOCK_ROWS,
        )

    def test_partial_stock_result_is_reported_to_user_and_in_sources(self) -> None:
        query = AgentCFOQuery(source="stock", item_type="product")
        plan = AgentCFOPlan(queries=[query])
        supabase = MagicMock()
        model_response = SimpleNamespace(
            text="He encontrado existencias de varios productos.",
            usage_metadata=None,
        )
        rows = [
            {
                "item_type": "product",
                "item_id": "P1",
                "item_name": "Cafetera",
                "warehouse_id": "A1",
                "warehouse_name": "Central",
                "units": 12,
            }
        ]

        with (
            patch.object(self.service, "_supabase", supabase),
            patch.object(self.service, "_plan_queries", return_value=plan),
            patch.object(
                self.service,
                "_execute_stock_query",
                return_value=(rows, False),
            ),
            patch.object(
                self.service._gemini.models,
                "generate_content",
                return_value=model_response,
            ) as generate_content,
        ):
            result = self.service._answer_question("Indica el stock", None)

        self.assertIn("la lista está incompleta", result.answer)
        self.assertIn(
            "resultado parcial: máximo de 50 ubicaciones",
            result.consulted_sources[0].reference,
        )
        evidence_prompt = generate_content.call_args.kwargs["contents"]
        self.assertIn('"query_results_complete": false', evidence_prompt)
        self.assertIn('"query_result_limit": 50', evidence_prompt)


if __name__ == "__main__":
    unittest.main()
