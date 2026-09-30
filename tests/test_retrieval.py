"""Tests for the score cutoff in src/vectorstore.py (no search, no model)."""

import config
from src.vectorstore import score_floor


def test_the_floor_is_the_cutoff_when_the_best_hit_is_weak():
    assert score_floor(0.60) == config.SCORE_THRESHOLD  # 0.60 - 0.10 is under the cutoff 0.58


def test_the_floor_is_the_margin_below_a_strong_best_hit():
    assert abs(score_floor(0.888) - (0.888 - config.SCORE_MARGIN)) < 1e-9
