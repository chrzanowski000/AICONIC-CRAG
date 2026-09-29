# Helios RAG: answers that admit what they don't know

A small question-answering demo over 20 made-up documents about a fictional company, Helios
Dynamics. Some documents disagree. Some are old and replaced by newer ones.

The system:

- answers with citations when the documents give one current answer,
- shows **both** versions with dates when two documents disagree, and does not pick one,
- prefers the newer document only when the older one is marked as replaced, and still mentions
  the old one,
- says "I don't know" when no document answers the question.

Work in progress. See `STATUS.md` for where things stand and `docs/` for how it works.
