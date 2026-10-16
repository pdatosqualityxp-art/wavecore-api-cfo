import os
import unittest
from datetime import date
from importlib import import_module
from unittest.mock import patch

from app.schemas.agent_cfo import AgentCFOContractCommitment

os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")

QUESTION = (
    "según el Contrato de ventas Aroma de Gracia, tenemos un nivel de stock "
    "saludable para cubrir el acuerdo?"
)
COMMITMENT = AgentCFOContractCommitment(
    found=True,
    product_name="Atlas2",
    monthly_units=3,
    customer_id="CLI0004",
    customer_name="Aroma de Gracia",
    start_date=date(2026, 1, 1),
    end_date=date(2027, 12, 31),
)
CHUNKS = [{"titulo": "Contrato Aroma de Gracia", "page_number": 1, "chunk_text": "x"}]


class AgentCFOContractStockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.service = import_module("app.services.agent_cfo_service")

    def _run(self, stock_rows, sales_rows, commitment=COMMITMENT, chunks=CHUNKS):
        with (
            patch.object(self.service, "search_document_chunks", return_value=chunks),
            patch.object(
                self.service, "_extract_contract_commitment", return_value=commitment
            ),
            patch.object(
                self.service, "_execute_stock_query", return_value=(stock_rows, True)
            ),
            patch.object(self.service, "_execute_query", return_value=sales_rows),
        ):
            return self.service._analyze_contract_stock(
                QUESTION, {}, today=date(2026, 10, 16)
            )

    @staticmethod
    def _stock(units: int, name: str = "Atlas2") -> list[dict[str, object]]:
        return [{"item_id": "PROD1", "item_name": name, "units": units}]

    def test_intent_requires_contract_and_stock_terms(self) -> None:
        self.assertTrue(self.service._CONTRACT_INTENT.search(QUESTION))
        self.assertTrue(self.service._CONTRACT_STOCK_INTENT.search(QUESTION))
        self.assertIsNone(self.service._CONTRACT_INTENT.search("stock de Atlas2"))

    def test_stock_covers_whole_remaining_commitment(self) -> None:
        answer, sources, consulted = self._run(
            self._stock(50), [{"group_label": "Atlas2", "units": 30}]
        )

        # octubre 2026 a diciembre 2027 = 15 meses * 3 = 45 unidades
        self.assertIn("Quedan 15 meses", answer)
        self.assertIn("45 unidades", answer)
        self.assertIn("cubre todo el compromiso pendiente", answer)
        self.assertIn("30 unidades compradas", answer)
        self.assertIn("27 esperadas", answer)
        self.assertEqual(sources[0].type, "pdf")
        self.assertEqual([item.type for item in consulted], ["pdf", "table", "table"])

    def test_stock_partially_covers_commitment(self) -> None:
        answer, _, _ = self._run(self._stock(10), [])

        self.assertIn("faltan 35 unidades", answer)
        self.assertIn("3 meses completos", answer)
        self.assertNotIn("compradas por el cliente", answer)

    def test_stock_below_next_month(self) -> None:
        answer, _, _ = self._run(self._stock(2), [])

        self.assertIn("no cubre ni el próximo mes", answer)

    def test_product_missing_from_stock(self) -> None:
        answer, _, _ = self._run([], [])

        self.assertIn("No encontré en la tabla de stock", answer)

    def test_ambiguous_product(self) -> None:
        rows = [
            {"item_id": "P1", "item_name": "Atlas2 Pro", "units": 4},
            {"item_id": "P2", "item_name": "Atlas2 Mini", "units": 9},
        ]
        answer, _, _ = self._run(rows, [])

        self.assertIn("varios productos", answer)

    def test_commitment_not_found(self) -> None:
        answer, _, _ = self._run(
            [], [], commitment=AgentCFOContractCommitment(found=False)
        )

        self.assertIn("No pude identificar", answer)

    def test_contract_not_found(self) -> None:
        answer, _, _ = self._run([], [], chunks=[])

        self.assertIn("No encontré el contrato", answer)

    def test_expired_contract(self) -> None:
        expired = COMMITMENT.model_copy(update={"end_date": date(2026, 6, 30)})
        answer, _, _ = self._run(self._stock(5), [], commitment=expired)

        self.assertIn("ya no queda compromiso pendiente", answer)

    def test_found_commitment_requires_product_and_units(self) -> None:
        with self.assertRaises(ValueError):
            AgentCFOContractCommitment(found=True)


if __name__ == "__main__":
    unittest.main()
