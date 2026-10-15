from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AgentCFORequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(min_length=1, max_length=2000)


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
        "compras",
        "estados_intervencion",
        "servicios_intervencion",
        "establecimientos",
        "intervenciones",
        "sales",
        "purchases",
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


class AgentCFOSource(BaseModel):
    id: str
    type: Literal["pdf", "products", "table", "sales", "purchases", "stock"]
    reference: str
    details: dict[str, object]


class AgentCFOConsultedSource(BaseModel):
    type: Literal["pdf", "table"]
    reference: str


class AgentCFOResponse(BaseModel):
    answer: str
    model: str
    sources: list[AgentCFOSource]
    consulted_sources: list[AgentCFOConsultedSource] = Field(default_factory=list)
