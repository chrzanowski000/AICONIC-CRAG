"""Unit tests for src/quantities.py: the number check behind the backstop and the answer check."""

import pytest

from src.quantities import numbers_clash, quantities


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # the basic cases from the corpus
        ("Helios Dynamics offers 16 weeks of fully paid parental leave.", {"week": {16}}),
        ("The daily meal allowance for business travel is $60 per day.", {"$": {60}}),
        ("Employees may work remotely up to two days per week.", {"day": {2}}),
        ("Passwords must be at least 14 characters long.", {"character": {14}}),
        ("Leave is paid at 100% of base salary.", {"%": {100}}),
        # decimals, thousands commas, several values for one unit
        ("It weighs 1.2 kg and costs $1,200.", {"kg": {1.2}, "$": {1200}}),
        ("12 weeks, 16 weeks", {"week": {12, 16}}),
        # numbers that are part of a name, or a clock time, are not quantities
        ("The Kestrel X2 flight time is up to 45 minutes.", {"minute": {45}}),
        ("Sev1 alerts must be acknowledged within 15 minutes.", {"minute": {15}}),
        ("The office is open from 7:00 to 20:00 on weekdays.", {}),
        # nothing to find
        ("Forced password changes on a schedule are switched off.", {}),
        ("", {}),
        (None, {}),
    ],
)
def test_quantities(text, expected):
    assert quantities(text) == expected


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        # same unit, different number: a clash
        ("16 weeks of fully paid parental leave", "12 weeks of paid parental leave", "16 vs 12 week"),
        ("$60 per day", "$75 per day", "60 vs 75 $"),
        ("up to two days per week", "up to 3 days per week", "2 vs 3 day"),
        ("paid at 100% of salary", "paid at 80% of salary", "100 vs 80 %"),
        # same number written differently: no clash
        ("Pull requests need 2 approvals.", "Pull requests need two approvals.", None),
        ("sixteen weeks of leave", "16 weeks of fully paid leave", None),
        # different units: no clash
        ("Flight time is up to 45 minutes.", "It weighs 1.2 kg and carries up to 300 g.", None),
        # a dispute in words has no numbers to compare: the judge must catch it
        ("Change your password every 90 days.", "There is no fixed schedule for password changes.", None),
    ],
)
def test_numbers_clash(a, b, expected):
    assert numbers_clash(a, b) == expected
