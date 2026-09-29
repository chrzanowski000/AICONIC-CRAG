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

COMPARE = """\
You check retrieved documents for a question-answering system. You never answer the question
yourself and never decide which document is right.
1. For EACH document decide whether its claim directly answers the question (relevant).
2. For EACH listed pair, compare the two claims only as answers to the question:
   - same: both give the same answer. The same value written differently ("two" and "2") is
     the same.
   - different: their answers cannot both be true. Check numbers, amounts, units, dates, names
     and rules exactly. In what_differs write one short sentence that names both values, for
     example "D03 says 16 weeks, D04 says 12 weeks".
   - unrelated: at least one does not answer the question, or they answer different parts of it.
Only the part that answers the question counts; details the question does not ask about do not
make a pair different. A newer date settles nothing. Return only the structured object."""

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


def compare_messages(question: str, docs: list[dict], claims: dict[str, str | None],
                     pairs: list[tuple[str, str]]) -> list:
    lines = [f"[{d['doc_id']}] {d['title']} — source: {d['source']} — date: {d['date']}\n"
             f"Claim: {claims.get(d['doc_id'])}" for d in docs]
    listed = ", ".join(f"{a}-{b}" for a, b in pairs) or "none"
    return [SystemMessage(COMPARE),
            HumanMessage(f"Question: {question}\n\nDocuments with their claims:\n"
                         + "\n\n".join(lines) + f"\n\nPairs to compare: {listed}")]


def answer_messages(question: str, docs: list[dict], claims: dict[str, str | None]) -> list:
    lines = [f"[{d['doc_id']}] {d['title']} — source: {d['source']} — date: {d['date']}\n"
             f"Claim: {claims.get(d['doc_id']) or '(no claim)'}" for d in docs]
    return [SystemMessage(ANSWER),
            HumanMessage(f"Question: {question}\n\nClaims:\n" + "\n\n".join(lines))]


CHECK_ANSWER = """\
You check an answer written for a question-answering system. The answer must be written from the
claims only. List every problem of these two kinds:
1. The answer states a fact that none of the claims states.
2. The answer writes a value (a number, amount, date or name) that the full documents give
   differently from each other. Stating one of the values picks a side. Only a value written in
   the answer counts: words that name no value, such as "the whole period" or "full pay", are
   not a problem.
Do not list style, missing details or citations. Return an empty list if there is no problem.
Return only the structured object."""


def check_answer_messages(question: str, answer: str, docs: list[dict],
                          claims: dict[str, str | None]) -> list:
    claim_lines = "\n".join(f"[{d['doc_id']}] {claims.get(d['doc_id']) or '(no claim)'}" for d in docs)
    full = "\n\n".join(format_doc(d) for d in docs)
    return [SystemMessage(CHECK_ANSWER),
            HumanMessage(f"Question: {question}\n\nAnswer: {answer}\n\nClaims:\n{claim_lines}"
                         f"\n\nFull documents:\n{full}")]
