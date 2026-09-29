"""Prompt texts. Kept short and literal on purpose."""

from langchain_core.messages import HumanMessage, SystemMessage

EXTRACT_CLAIMS = """\
You pull claims out of documents for a question-answering system. You never answer the question
yourself and never judge which document is right.
For EACH document, say in one sentence what that document says in answer to the question. Keep
only the part that answers the question; leave out details the question does not ask about, such
as other numbers, amounts or conditions. Copy numbers, amounts, dates and names exactly as
written. If a document says nothing about the question, return null for it. Return only the
structured object."""

ASSESS = """\
You check retrieved documents for a question-answering system. You never answer the question
yourself.
For EACH document decide whether it directly answers the question (relevant).
Then compare every pair of relevant documents. If two documents give answers to the question that
cannot both be true (different numbers, different names, opposite rules), list the pair under
conflicts. Only the part that answers the question counts; differences in details the question
does not ask about are not conflicts. Do NOT settle conflicts, do NOT guess which is right, and
do NOT treat a newer date as settling anything.
Known "replaces" links (already handled, do NOT list them as conflicts): {supersession_facts}
Return only the structured object."""

ANSWER = """\
Answer the question using ONLY the claims below. Each claim is what one document says about the
question. Every factual statement must end with the id of the document it comes from in square
brackets, e.g. [D14]. If the claims do not fully answer the question, say what is missing instead
of guessing. Answer only what the question asks; do not add other details. Do not mention
documents that are not listed."""


def format_doc(doc: dict) -> str:
    """One document as the LLM sees it: a header line with the metadata, then the text."""
    return (f"### [{doc['doc_id']}] {doc['title']} — source: {doc['source']} — "
            f"date: {doc['date']} — supersedes: {doc.get('supersedes') or 'none'}\n{doc['text']}")


def extract_claims_messages(question: str, docs: list[dict]) -> list:
    body = "\n\n".join(format_doc(d) for d in docs)
    return [SystemMessage(EXTRACT_CLAIMS),
            HumanMessage(f"Question: {question}\n\nDocuments:\n{body}")]


def assess_messages(question: str, docs: list[dict], claims: dict[str, str | None],
                    supersession_facts: str) -> list:
    lines = [f"[{d['doc_id']}] {d['title']} — source: {d['source']} — date: {d['date']}\n"
             f"Claim: {claims.get(d['doc_id']) or 'null'}" for d in docs]
    return [SystemMessage(ASSESS.format(supersession_facts=supersession_facts or "none")),
            HumanMessage(f"Question: {question}\n\nDocuments with their claims:\n"
                         + "\n\n".join(lines))]


def answer_messages(question: str, docs: list[dict], claims: dict[str, str | None]) -> list:
    lines = [f"[{d['doc_id']}] {d['title']} — source: {d['source']} — date: {d['date']}\n"
             f"Claim: {claims.get(d['doc_id']) or '(no claim)'}" for d in docs]
    return [SystemMessage(ANSWER),
            HumanMessage(f"Question: {question}\n\nClaims:\n" + "\n\n".join(lines))]
