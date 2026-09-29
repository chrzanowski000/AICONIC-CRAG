"""Pydantic models: what the LLM must return, what Jev sends and returns, and the final output."""

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


# LLM judge (used when JUDGE=llm, or when Jev fails)


class DocAssessment(BaseModel):
    doc_id: str
    relevant: bool = Field(
        description="True only if the document says something that directly answers the question"
    )


class Conflict(BaseModel):
    doc_a: str
    doc_b: str
    description: str


class Assessment(BaseModel):
    docs: list[DocAssessment]
    conflicts: list[Conflict] = Field(
        description="Every pair of RELEVANT documents whose claims cannot both be true"
    )


# --- Jev Decisions API -----------------------------------------------------------------------


class JevDocument(BaseModel):
    id: str
    source: str
    date: str
    claim: str


class JevState(BaseModel):
    question: str
    documents: list[JevDocument]


class JevQuestion(BaseModel):
    type: Literal["noul", "choice"]
    instructions: str
    criteria: dict[str, str] | None = None


class JevRequest(BaseModel):
    model: str
    state: JevState
    questions: dict[str, JevQuestion]


class JevAnswer(BaseModel):
    type: Literal["noul", "choice"]
    noul: float | None = None
    choice: str | None = None
    confidence: float | None = None
    probabilities: dict[str, float] | None = None


class JevUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0


class JevResponse(BaseModel):
    answers: dict[str, JevAnswer]
    id: str | None = None
    model: str | None = None
    provider: str | None = None
    usage: JevUsage = JevUsage()


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
    reason: str | None = None
