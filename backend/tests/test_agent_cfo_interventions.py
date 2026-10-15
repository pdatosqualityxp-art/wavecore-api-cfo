import os
import unittest
from datetime import date
from importlib import import_module
from unittest.mock import MagicMock, patch

from app.schemas.agent_cfo import AgentCFOPlan, AgentCFOQuery

os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")


class AgentCFOInterventionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.service = import_module("app.services.agent_cfo_service")

    def test_count_for_establishment_routes_to_complete_aggregate(self) -> None:
        plan = AgentCFOPlan(
            queries=[
                AgentCFOQuery(
                    source="intervenciones",
                    start_date=date(2026, 1, 1),
                    end_date=date(2026, 6, 30),
                ),
                AgentCFOQuery(source="establecimientos"),
            ]
        )

        routed_plan = self.service._ensure_explicit_sources(
            "El ESTAB0016 tiene varias intervenciones, ¿cuántas tiene?",
            plan,
        )

        self.assertEqual(len(routed_plan.queries), 1)
        query = routed_plan.queries[0]
        self.assertEqual(query.source, "intervention_counts")
        self.assertEqual(query.search_term, "ESTAB0016")
        self.assertEqual(query.start_date, date(2026, 1, 1))
        self.assertEqual(query.end_date, date(2026, 6, 30))

    def test_ranking_routes_to_aggregate_for_all_establishments(self) -> None:
        plan = AgentCFOPlan(
            queries=[
                AgentCFOQuery(source="intervenciones"),
                AgentCFOQuery(source="establecimientos"),
            ]
        )

        routed_plan = self.service._ensure_explicit_sources(
            "¿Qué establecimiento tiene más intervenciones?",
            plan,
        )

        self.assertEqual(len(routed_plan.queries), 1)
        self.assertEqual(routed_plan.queries[0].source, "intervention_counts")
        self.assertIsNone(routed_plan.queries[0].search_term)

    def test_intervention_aggregate_uses_read_only_rpc(self) -> None:
        query = AgentCFOQuery(
            source="intervention_counts",
            search_term="ESTAB0016",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
        )
        rows = [
            {
                "id_establecimiento": "ESTAB0016",
                "establecimiento": "Tienda Barcelona",
                "intervention_count": 8,
            }
        ]
        supabase = MagicMock()
        supabase.rpc.return_value.execute.return_value.data = rows

        with patch.object(self.service, "_supabase", supabase):
            result = self.service._execute_query(query, "¿Cuántas intervenciones?")

        self.assertEqual(result, rows)
        supabase.rpc.assert_called_once_with(
            "agent_cfo_interventions_report",
            {
                "p_search": "ESTAB0016",
                "p_start_date": "2026-01-01",
                "p_end_date": "2026-06-30",
                "p_limit": 8,
            },
        )

    def test_aggregate_rows_are_presented_as_establishment_counts(self) -> None:
        query = AgentCFOQuery(source="intervention_counts")
        rows = [
            {
                "id_establecimiento": "ESTAB0016",
                "establecimiento": "Tienda Barcelona",
                "intervention_count": 8,
            }
        ]

        sources = self.service._make_sources(query, rows, next_id=1)

        self.assertEqual(sources[0].type, "table")
        self.assertEqual(
            sources[0].reference,
            "Intervenciones de Tienda Barcelona: 8",
        )


if __name__ == "__main__":
    unittest.main()
