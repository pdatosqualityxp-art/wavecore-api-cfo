import os
import unittest
from importlib import import_module
from unittest.mock import MagicMock, patch

from app.schemas.agent_cfo import AgentCFOQuery

os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")


class AgentCFOProductsTests(unittest.TestCase):
    def setUp(self) -> None:
        module = import_module("app.services.agent_cfo_service")
        for name, value in (("_TABLE_PAGE_SIZE", 10), ("_MAX_TABLE_ROWS", 50)):
            patcher = patch.object(module, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    @classmethod
    def setUpClass(cls) -> None:
        cls.service = import_module("app.services.agent_cfo_service")

    def test_product_catalog_query_uses_read_only_rpc_with_pagination(self) -> None:
        query = AgentCFOQuery(
            source="products",
            search_term="café",
            limit=5,
        )
        supabase = MagicMock()
        supabase.rpc.return_value.execute.return_value.data = [
            {
                "id_prod": "P1",
                "nom_prod": "Cafetera",
                "desc_prod": "Cafetera automática",
                "precio_prod": 90.0,
            }
        ]

        with patch.object(self.service, "_supabase", supabase):
            rows = self.service._execute_query(query, "Busca cafeteras")

        self.assertEqual(rows[0]["id_prod"], "P1")
        supabase.rpc.assert_called_once_with(
            "agent_cfo_products_catalog",
            {"p_search": "café", "p_limit": 10, "p_offset": 0},
        )

    def test_product_catalog_rows_are_returned_as_product_sources(self) -> None:
        query = AgentCFOQuery(source="products")
        rows = [
            {
                "id_prod": "P1",
                "nom_prod": "Cafetera",
                "desc_prod": "Cafetera automática",
                "precio_prod": 90.0,
            }
        ]

        sources = self.service._make_sources(query, rows, next_id=1)

        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0].type, "products")
        self.assertEqual(sources[0].reference, "Producto: Cafetera")
        self.assertEqual(sources[0].details, rows[0])

    def test_direct_table_query_uses_allowlisted_read_rpc(self) -> None:
        query = AgentCFOQuery(
            source="almacen",
            search_term="Madrid",
            limit=4,
        )
        supabase = MagicMock()
        supabase.rpc.return_value.execute.return_value.data = [
            {
                "row_data": {
                    "id_alm": "A1",
                    "nom_alm": "Almacén Madrid",
                    "poblacion_alm": "Madrid",
                }
            }
        ]

        with patch.object(self.service, "_supabase", supabase):
            rows = self.service._execute_query(query, "¿Puedes ver almacen?")

        self.assertEqual(rows[0]["table"], "almacen")
        self.assertEqual(rows[0]["id_alm"], "A1")
        supabase.rpc.assert_called_once_with(
            "agent_cfo_table_read",
            {
                "p_table": "almacen",
                "p_search": "Madrid",
                "p_start_date": None,
                "p_end_date": None,
                "p_limit": 10,
                "p_offset": 0,
            },
        )

    def test_direct_table_records_are_identified_in_sources(self) -> None:
        query = AgentCFOQuery(source="almacen")
        sources = self.service._make_sources(
            query,
            [{"table": "almacen", "id_alm": "A1", "nom_alm": "Central"}],
            next_id=1,
        )

        self.assertEqual(sources[0].type, "table")
        self.assertEqual(sources[0].reference, "almacen: A1")

    def test_direct_table_query_collects_multiple_pages(self) -> None:
        query = AgentCFOQuery(source="componentes")
        first_page = [
            {"row_data": {"id_compo": f"C{index:02d}"}}
            for index in range(10)
        ]
        second_page = [
            {"row_data": {"id_compo": f"C{index:02d}"}}
            for index in range(10, 12)
        ]

        with patch.object(
            self.service,
            "_rpc_rows",
            side_effect=[first_page, second_page],
        ) as rpc_rows:
            rows, complete = self.service._execute_table_query(query)

        self.assertEqual(len(rows), 12)
        self.assertTrue(complete)
        self.assertEqual(rows[0]["table"], "componentes")
        self.assertEqual(
            [call.args[1]["p_offset"] for call in rpc_rows.call_args_list],
            [0, 10],
        )

    def test_direct_table_query_reports_when_maximum_is_exceeded(self) -> None:
        query = AgentCFOQuery(source="clientes")
        pages = [
            [
                {"row_data": {"id_cliente": f"CLI{offset + index:04d}"}}
                for index in range(10)
            ]
            for offset in range(0, self.service._MAX_TABLE_ROWS, 10)
        ]
        with patch.object(
            self.service,
            "_rpc_rows",
            side_effect=[*pages, [{"row_data": {"id_cliente": "CLI0051"}}]],
        ) as rpc_rows:
            rows, complete = self.service._execute_table_query(query)

        self.assertEqual(len(rows), self.service._MAX_TABLE_ROWS)
        self.assertFalse(complete)
        self.assertEqual(
            rpc_rows.call_args_list[-1].args[1]["p_offset"],
            self.service._MAX_TABLE_ROWS,
        )
        self.assertEqual(rpc_rows.call_args_list[-1].args[1]["p_limit"], 1)


if __name__ == "__main__":
    unittest.main()
