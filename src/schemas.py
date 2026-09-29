"""Pydantic models: what the LLM must return, and the final output."""

from typing import Literal

from pydantic import BaseModel, Field

# --- LLM output ------------------------------------------------------------------------------


class DocClaim(BaseModel):
    doc_id: str = Field(description="The document id, e.g. D03")
    claim: str | None = Field(
        description=(
            "What this document says in answer to the question, in one sentence, with numbers, "
            "amounts, dates and names copied exactly as written; only the part that answers the "
            "question, not other details; null if the document says nothing about the question"
        )
    )


class Claims(BaseModel):
    claims: list[DocClaim]


class Answer(BaseModel):
    answer: str = Field(
        description=(
            "2-4 sentences; every factual statement ends with the id of its source document in "
            "square brackets, e.g. [D14]. These ids are the citations."
        )
    )


# LLM judge: relevance of each doc, and each pair of claims compared


class DocAssessment(BaseModel):
    doc_id: str
    relevant: bool = Field(
        description="True only if the document's claim directly answers the question"
    )


class PairComparison(BaseModel):
    doc_a: str
    doc_b: str
    verdict: Literal["same", "different", "unrelated"] = Field(
        description=(
            "same: both give the same answer to the question; different: their answers cannot "
            "both be true; unrelated: at least one does not answer the question, or they answer "
            "different parts of it"
        )
    )
    what_differs: str | None = Field(
        description=(
            "Only when different: one short sentence that names both values, e.g. "
            "'D03 says 16 weeks, D04 says 12 weeks'. Null otherwise."
        )
    )


class Comparison(BaseModel):
    docs: list[DocAssessment]
    pairs: list[PairComparison] = Field(description="One entry for every listed pair")


# --- final output ----------------------------------------------------------------------------


class Citation(BaseModel):
    doc_id: str
    date: str
    source: str
    claim: str


class OutdatedNote(BaseModel):
    old_id: str
    old_date: str
    old_claim: str
    new_id: str
    new_date: str


class FinalOutput(BaseModel):
    status: Literal["answered", "disputed", "abstained"]
    answer: str | None = None  # answered only
    citations: list[Citation] = []  # answered: at least 1
    versions: list[Citation] = []  # disputed: at least 2
    outdated: list[OutdatedNote] = []
    differences: list[str] = []  # disputed: what differs, in words
    reason: str | None = None
