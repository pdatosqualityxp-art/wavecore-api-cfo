import os
import unittest
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")


class AgentCFOPDFRetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.vector_service = import_module("app.services.vector_service")
        cls.agent_service = import_module("app.services.agent_cfo_service")
        cls.query_model = import_module("app.schemas.agent_cfo").AgentCFOQuery

    def test_vector_search_passes_pdf_filters_to_supabase_rpc(self) -> None:
        response = SimpleNamespace(
            embeddings=[SimpleNamespace(values=[0.25] * 768)]
        )
        rpc_result = SimpleNamespace(data=[{"page_number": 16}])
        supabase = MagicMock()
        supabase.rpc.return_value.execute.return_value = rpc_result

        with (
            patch.object(
                self.vector_service._gemini.models,
                "embed_content",
                return_value=response,
            ),
            patch.object(self.vector_service, "_supabase", supabase),
        ):
            rows = self.vector_service.search_document_chunks(
                "EBITDA de gestión",
                match_count=8,
                document_title="titulo",
                page_number=16,
            )

        self.assertEqual(rows, [{"page_number": 16}])
        supabase.rpc.assert_called_once_with(
            "match_document_chunks_filtered",
            {
                "query_embedding": [0.25] * 768,
                "match_count": 8,
                "p_document_title": "titulo",
                "p_page_number": 16,
            },
        )

    def test_agent_forwards_planned_title_and_page_to_pdf_search(self) -> None:
        query = self.query_model(
            source="documents",
            document_title="titulo",
            page_number=16,
        )
        expected_rows = [{"titulo": "titulo", "page_number": 16}]

        with patch.object(
            self.agent_service,
            "search_document_chunks",
            return_value=expected_rows,
        ) as search:
            rows = self.agent_service._execute_query(
                query,
                "EBITDA de gestión",
            )

        self.assertEqual(rows, expected_rows)
        search.assert_called_once_with(
            "EBITDA de gestión",
            match_count=8,
            document_title="titulo",
            page_number=16,
        )


if __name__ == "__main__":
    unittest.main()
