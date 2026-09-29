"""Numbers in a sentence, grouped by what they count.

    quantities("Helios offers 16 weeks of paid leave")   -> {"week": {16.0}}
    quantities("The meal allowance is $60 per day")      -> {"$": {60.0}}
    numbers_clash("... 16 weeks ...", "... 12 weeks ...") -> "16 vs 12 week"

`src/graph.py` uses this for two safety checks that do not rely on a model:

- the number check in `reconcile`: two current claims on the same topic that give different
  numbers for the same unit become a dispute, even if the judge missed it;
- the check on the answer: the answer must not state a number that the documents disagree on.

The scope is small on purpose: short, plain English sentences, and one question only ("same
unit, different number?"). It is not a general number or unit parser.
"""

import re

Quantities = dict[str, set[float]]

WORD_NUMBERS: dict[str, int] = {
    **{word: value for value, word in enumerate(
        "zero one two three four five six seven eight nine ten eleven twelve thirteen "
        "fourteen fifteen sixteen seventeen eighteen nineteen twenty".split())},
    "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "ninety": 90,
}

# Words that can stand between a number and its unit and are not the unit themselves:
# "up to three days", "16 fully paid weeks", "at least 14 characters".
FILLER_WORDS = frozenset({
    "a", "an", "the", "of", "or", "and", "to", "in", "on", "at", "for", "per", "up",
    "about", "only", "least", "more", "less", "than", "full", "fully", "paid",
})

CURRENCY_SIGNS = "$€£"

_QUANTITY = re.compile(
    r"""
    (?P<currency>[CURRENCY])?\s?
    (?<![A-Za-z0-9:.,])                  # not part of a name or code ("Kestrel X2", "Sev1")
    (?P<number>
        \d{1,3}(?:,\d{3})+ (?![\d:])     # with thousands commas: 1,200
      | \d+(?:\.\d+)?      (?![\d:])     # 16, 1.2 (but not the hour in 7:00)
      | \b(?:WORDS)\b                    # written out: sixteen
    )
    (?P<after>(?:\s*%)?(?:[\s-]+[A-Za-z]+){0,3})   # "%" and up to three words after it
    """
    .replace("CURRENCY", CURRENCY_SIGNS)
    .replace("WORDS", "|".join(WORD_NUMBERS)),
    re.IGNORECASE | re.VERBOSE,
)


def _to_number(text: str) -> float:
    text = text.lower()
    if text in WORD_NUMBERS:
        return float(WORD_NUMBERS[text])
    return float(text.replace(",", ""))


def _singular(word: str) -> str:
    return word.rstrip("s") or word


def _unit(currency: str | None, after: str) -> str | None:
    """What a number counts: the currency sign, "%", or the first real word after it."""
    if currency:
        return currency
    if after.lstrip().startswith("%"):
        return "%"
    words = [w for w in re.findall(r"[a-z]+", after.lower()) if w not in FILLER_WORDS]
    return _singular(words[0]) if words else None


def quantities(text: str | None) -> Quantities:
    """Every number in `text` that has a unit, as {unit: {values}}."""
    found: Quantities = {}
    for match in _QUANTITY.finditer(text or ""):
        unit = _unit(match.group("currency"), match.group("after") or "")
        if unit is not None:
            found.setdefault(unit, set()).add(_to_number(match.group("number")))
    return found


def show_values(values: set[float]) -> str:
    """{12.0, 16.0} -> "12/16"."""
    return "/".join(f"{v:g}" for v in sorted(values))


def clashing_units(qa: Quantities, qb: Quantities) -> list[str]:
    """The units that both give, with different numbers."""
    return sorted(unit for unit in qa.keys() & qb.keys() if qa[unit] != qb[unit])


def numbers_clash(a: str, b: str) -> str | None:
    """If both texts give different numbers for the same unit, say how ("16 vs 12 week")."""
    qa, qb = quantities(a), quantities(b)
    units = clashing_units(qa, qb)
    if not units:
        return None
    unit = units[0]
    return f"{show_values(qa[unit])} vs {show_values(qb[unit])} {unit}"
