from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AgentCFORequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(min_length=1, max_length=2000)


class AgentCFOQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: Literal["documents", "sales", "purchases", "stock"]
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
        if self.source == "stock" and self.item_type is None:
            raise ValueError("Stock queries must specify product or component")
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
    type: Literal["pdf", "sales", "purchases", "stock"]
    reference: str
    details: dict[str, object]


class AgentCFOResponse(BaseModel):
    answer: str
    sources: list[AgentCFOSource]
