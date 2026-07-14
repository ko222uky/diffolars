"""
Unit tests for the `diffolars.demo` module, focused on `get_df_pair`.
"""

# Imports
from diffolars.demo import get_df_pair

SEED = 42

#————— Test Functions —————#

def test_get_df_pair_returns_original_and_mutated():
    """get_df_pair should return a dict with 'original' and 'mutated' frames."""
    pair = get_df_pair(n_rows=10, n_cols=4, seed=SEED)
    assert set(pair.keys()) == {"original", "mutated"}

def test_get_df_pair_shapes():
    """Row/column counts should reflect n_rows/n_cols plus any requested additions."""
    pair = get_df_pair(n_rows=10, n_cols=4, n_new_rows=3, n_new_cols=2, seed=SEED)

    # +1 column for "record_id" in both frames.
    assert pair["original"].shape == (10, 5)
    assert pair["mutated"].shape == (13, 7)

def test_get_df_pair_reproducible_with_same_seed():
    """Calling get_df_pair twice with the same seed should give identical frames.

    "record_id" is excluded from the comparison: it's always a fresh uuid4,
    not drawn from the seeded rng, so it's never reproducible by design.
    """
    pair_a = get_df_pair(n_rows=10, n_cols=4, n_new_rows=3, n_new_cols=2, seed=SEED)
    pair_b = get_df_pair(n_rows=10, n_cols=4, n_new_rows=3, n_new_cols=2, seed=SEED)

    assert pair_a["original"].drop("record_id").equals(pair_b["original"].drop("record_id"))
    assert pair_a["mutated"].drop("record_id").equals(pair_b["mutated"].drop("record_id"))

def test_get_df_pair_different_seeds_differ():
    """Different seeds should (almost certainly) produce different data."""
    pair_a = get_df_pair(n_rows=10, n_cols=4, seed=SEED)
    pair_b = get_df_pair(n_rows=10, n_cols=4, seed=SEED + 1)

    assert not pair_a["original"].drop("record_id").equals(pair_b["original"].drop("record_id"))
