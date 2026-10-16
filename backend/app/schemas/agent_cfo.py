from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AgentCFORequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(min_length=1, max_length=2000)
    conversation_id: UUID | None = None


class AgentCFOQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: Literal[
        "documents",
        "products",
        "clientes",
        "proveedores_compo",
        "proveedores_serv",
        "componentes",
        "almacen",
        "stock_prod",
        "stock_compo",
        "ventas",
        "customer_sales",
        "compras",
        "estados_intervencion",
        "servicios_intervencion",
        "establecimientos",
        "intervenciones",
        "sales",
        "purchases",
        "stock_coverage",
        "table_count",
        "intervention_counts",
        "stock",
    ]
    table_name: Literal[
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
    ] | None = None
    start_date: date | None = None
    end_date: date | None = None
    group_by: Literal[
        "total",
        "month",
        "product",
        "customer",
        "component",
        "supplier",
    ] | None = None
    filter_by: Literal["product", "customer", "component", "supplier"] | None = None
    item_type: Literal["product", "component"] | None = None
    document_title: str | None = Field(default=None, max_length=255)
    page_number: int | None = Field(default=None, ge=1)
    search_term: str | None = Field(default=None, max_length=100)
    warehouse: str | None = Field(default=None, max_length=100)
    limit: int = Field(default=8, ge=1, le=10)

    @model_validator(mode="after")
    def validate_query_scope(self) -> "AgentCFOQuery":
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.start_date > self.end_date
        ):
            raise ValueError("start_date must not be after end_date")

        if self.source == "sales" and self.group_by not in {
            None,
            "total",
            "month",
            "product",
            "customer",
        }:
            raise ValueError("Unsupported sales grouping")
        if self.source == "sales" and self.filter_by not in {
            None,
            "product",
            "customer",
        }:
            raise ValueError("Unsupported sales filter")
        if self.source == "purchases" and self.group_by not in {
            None,
            "total",
            "month",
            "component",
            "supplier",
        }:
            raise ValueError("Unsupported purchases grouping")
        if self.source == "purchases" and self.filter_by not in {
            None,
            "component",
            "supplier",
        }:
            raise ValueError("Unsupported purchases filter")
        if self.group_by is not None and self.source not in {"sales", "purchases"}:
            raise ValueError("Grouping is only valid for sales or purchases reports")
        if self.filter_by is not None and self.source not in {"sales", "purchases"}:
            raise ValueError("Entity filters are only valid for sales or purchases")
        if (
            (self.start_date is not None or self.end_date is not None)
            and self.source not in {
                "sales",
                "purchases",
                "customer_sales",
                "ventas",
                "compras",
                "intervenciones",
                "intervention_counts",
                "table_count",
            }
        ):
            raise ValueError("Date filters are not valid for this source")
        if (
            self.source == "table_count"
            and (self.start_date is not None or self.end_date is not None)
            and self.table_name not in {"ventas", "compras", "intervenciones"}
        ):
            raise ValueError("Date filters are only valid for transactional counts")
        if self.source == "stock" and self.item_type is None:
            raise ValueError("Stock queries must specify product or component")
        if self.source == "table_count" and self.table_name is None:
            raise ValueError("Table count queries must specify a table")
        if self.source == "customer_sales" and not self.search_term:
            raise ValueError("Customer sales queries must specify a customer name")
        if self.source == "customer_sales" and not self.search_term.strip():
            raise ValueError("Customer name must not be empty")
        if self.source != "table_count" and self.table_name is not None:
            raise ValueError("table_name is only valid for table counts")
        if self.item_type is not None and self.source != "stock":
            raise ValueError("item_type is only valid for stock reports")
        if self.warehouse is not None and self.source != "stock":
            raise ValueError("warehouse is only valid for stock reports")
        if self.source != "documents" and (
            self.document_title is not None or self.page_number is not None
        ):
            raise ValueError("Document filters are only valid for PDF queries")
        return self


class AgentCFOPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    queries: list[AgentCFOQuery] = Field(max_length=4)


class AgentCFOContractCommitment(BaseModel):
    """Compromiso de compra extraído de un contrato PDF."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    found: bool
    product_name: str | None = Field(default=None, max_length=100)
    monthly_units: int | None = Field(default=None, ge=1, le=1_000_000)
    customer_id: str | None = Field(default=None, max_length=50)
    customer_name: str | None = Field(default=None, max_length=255)
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def validate_commitment(self) -> "AgentCFOContractCommitment":
        if self.found and (not self.product_name or self.monthly_units is None):
            raise ValueError("A found commitment needs product_name and monthly_units")
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.start_date > self.end_date
        ):
            raise ValueError("start_date must not be after end_date")
        return self


class AgentCFOSource(BaseModel):
    id: str
    type: Literal["pdf", "products", "table", "sales", "purchases", "stock"]
    reference: str
    details: dict[str, object]


class AgentCFOConsultedSource(BaseModel):
    type: Literal["pdf", "table", "document"]
    reference: str


class AgentCFOResponse(BaseModel):
    answer: str
    model: str
    conversation_id: UUID
    sources: list[AgentCFOSource]
    consulted_sources: list[AgentCFOConsultedSource] = Field(default_factory=list)
