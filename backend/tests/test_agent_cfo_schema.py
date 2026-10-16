import unittest
from datetime import date
from uuid import UUID

from pydantic import ValidationError

from app.schemas.agent_cfo import AgentCFOPlan, AgentCFOQuery, AgentCFORequest


class AgentCFORequestTests(unittest.TestCase):
    def test_request_trims_question_whitespace(self) -> None:
        request = AgentCFORequest(question="  ¿Cuáles fueron las ventas?  ")

        self.assertEqual(request.question, "¿Cuáles fueron las ventas?")
        self.assertIsNone(request.conversation_id)

    def test_request_accepts_conversation_uuid(self) -> None:
        conversation_id = UUID("490af1b6-7b43-4b09-a941-a528ee5bf7bf")
        request = AgentCFORequest(
            question="¿Y se vende mucho?",
            conversation_id=conversation_id,
        )

        self.assertEqual(request.conversation_id, conversation_id)

    def test_plan_accepts_supported_sales_and_stock_queries(self) -> None:
        plan = AgentCFOPlan(
            queries=[
                {
                    "source": "sales",
                    "group_by": "month",
                    "start_date": date(2026, 1, 1),
                    "end_date": date(2026, 3, 31),
                },
                {
                    "source": "stock",
                    "item_type": "product",
                    "search_term": "monitor",
                },
            ]
        )

        self.assertEqual(len(plan.queries), 2)

    def test_plan_rejects_unsupported_sales_grouping(self) -> None:
        with self.assertRaises(ValidationError):
            AgentCFOQuery(source="sales", group_by="supplier")

    def test_plan_rejects_stock_query_without_item_type(self) -> None:
        with self.assertRaises(ValidationError):
            AgentCFOQuery(source="stock")

    def test_stock_coverage_query_accepts_product_context_to_be_resolved(self) -> None:
        query = AgentCFOQuery(
            source="stock_coverage",
            search_term=None,
        )

        self.assertIsNone(query.search_term)

    def test_document_query_accepts_title_and_page_filters(self) -> None:
        query = AgentCFOQuery(
            source="documents",
            document_title="titulo",
            page_number=16,
        )

        self.assertEqual(query.document_title, "titulo")
        self.assertEqual(query.page_number, 16)

    def test_document_filters_are_rejected_for_relational_sources(self) -> None:
        with self.assertRaises(ValidationError):
            AgentCFOQuery(
                source="sales",
                document_title="titulo",
                page_number=16,
            )

    def test_plan_rejects_reversed_date_range(self) -> None:
        with self.assertRaises(ValidationError):
            AgentCFOQuery(
                source="sales",
                start_date=date(2026, 3, 1),
                end_date=date(2026, 1, 1),
            )

    def test_plan_rejects_unrecognized_query_fields(self) -> None:
        with self.assertRaises(ValidationError):
            AgentCFOQuery(source="sales", sql="DROP TABLE ventas")

    def test_plan_requires_allowlisted_table_for_exact_count(self) -> None:
        query = AgentCFOQuery(source="table_count", table_name="clientes")

        self.assertEqual(query.table_name, "clientes")
        with self.assertRaises(ValidationError):
            AgentCFOQuery(source="table_count")
        with self.assertRaises(ValidationError):
            AgentCFOQuery(source="table_count", table_name="chat_logs")

    def test_plan_accepts_direct_read_of_every_business_table(self) -> None:
        tables = [
            "clientes",
            "proveedores_compo",
            "proveedores_serv",
            "productos",
            "componentes",
            "almacen",
            "stock_prod",
            "stock_compo",
            "ventas",
            "compras",
            "estados_intervencion",
            "servicios_intervencion",
            "establecimientos",
            "intervenciones",
        ]

        for table in tables:
            source = "products" if table == "productos" else table
            with self.subTest(table=table):
                query = AgentCFOQuery(source=source)
                self.assertEqual(query.source, source)


if __name__ == "__main__":
    unittest.main()
