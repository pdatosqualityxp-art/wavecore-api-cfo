import os
import unittest
from importlib import import_module
from unittest.mock import MagicMock, patch

from app.schemas.agent_cfo import AgentCFOPlan, AgentCFOQuery

os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")


class AgentCFOTableCountTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.service = import_module("app.services.agent_cfo_service")

    def test_component_count_is_forced_to_exact_table_count(self) -> None:
        plan = AgentCFOPlan(
            queries=[AgentCFOQuery(source="componentes")]
        )

        routed = self.service._ensure_explicit_sources(
            "¿Cuántos componentes hay?",
            plan,
        )

        self.assertEqual(len(routed.queries), 1)
        self.assertEqual(routed.queries[0].source, "table_count")
        self.assertEqual(routed.queries[0].table_name, "componentes")

    def test_client_count_is_forced_even_when_planner_omits_table_query(self) -> None:
        routed = self.service._ensure_explicit_sources(
            "¿Cuántos clientes hay?",
            AgentCFOPlan(queries=[]),
        )

        self.assertEqual(len(routed.queries), 1)
        self.assertEqual(routed.queries[0].source, "table_count")
        self.assertEqual(routed.queries[0].table_name, "clientes")

    def test_sales_count_does_not_add_or_keep_sales_summary(self) -> None:
        routed = self.service._ensure_explicit_sources(
            "¿Cuántas ventas hay?",
            AgentCFOPlan(queries=[AgentCFOQuery(source="sales")]),
        )

        self.assertEqual(len(routed.queries), 1)
        self.assertEqual(routed.queries[0].source, "table_count")
        self.assertEqual(routed.queries[0].table_name, "ventas")

    def test_exact_count_calls_allowlisted_count_rpc(self) -> None:
        query = AgentCFOQuery(
            source="table_count",
            table_name="clientes",
            search_term="Madrid",
        )
        expected = [{"table_name": "clientes", "total_count": 12}]
        supabase = MagicMock()
        supabase.rpc.return_value.execute.return_value.data = expected

        with patch.object(self.service, "_supabase", supabase):
            result = self.service._execute_query(query, "¿Cuántos clientes hay?")

        self.assertEqual(result, expected)
        supabase.rpc.assert_called_once_with(
            "agent_cfo_table_count",
            {
                "p_table": "clientes",
                "p_search": "Madrid",
                "p_start_date": None,
                "p_end_date": None,
            },
        )

    def test_count_evidence_includes_exact_total(self) -> None:
        query = AgentCFOQuery(source="table_count", table_name="componentes")
        sources = self.service._make_sources(
            query,
            [{"table_name": "componentes", "total_count": 6}],
            next_id=1,
        )

        self.assertEqual(sources[0].reference, "Total en componentes: 6")
        self.assertEqual(sources[0].details["total_count"], 6)


if __name__ == "__main__":
    unittest.main()
