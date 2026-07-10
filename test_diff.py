"""
Unit tests for the `diffolars.diff` module.
"""

# Imports
import pytest
import polars as pl
from diffolars.diff import (
    brian_kernighan,
    bitwise_not,
    count_unpadded_zero_bits,
    count_zero_bits,
    get_row_list,
    row2num_bits,
    compute_bitarray64,
    count_bitarrays,
    column_intercept,
    column_symmetric_diff,
    row_intercept,
    row_symmetric_diff,
    bitdiff,
    pruned_rows,
)

#————— Bitarray Primitive Tests —————#

def test_brian_kernighan_counts_set_bits():
    """brian_kernighan should count the number of 1 bits."""
    assert brian_kernighan(0b1011) == 3
    assert brian_kernighan(0) == 0

def test_bitwise_not_flips_bits_within_minimal_width():
    """bitwise_not should only flip bits within the input's own bit width."""
    assert bitwise_not(0b101) == 0b010

def test_count_unpadded_zero_bits_counts_zero_bits():
    """count_unpadded_zero_bits should count 0 bits within the minimal bit width."""
    assert count_unpadded_zero_bits(0b101) == 1

def test_count_unpadded_zero_bits_zero_input_returns_one():
    """A bitarray of 0 is a special case that always counts as one zero bit."""
    assert count_unpadded_zero_bits(0) == 1

def test_count_zero_bits_given_bit_width():
    """count_zero_bits should subtract the set-bit count from the given bit width."""
    assert count_zero_bits(0b101, num_bits=4) == 2

#————— Row / Bitarray Construction Tests —————#

def test_get_row_list_returns_non_id_values_in_order():
    """get_row_list should strip id columns and preserve the remaining order."""
    row = {"col_0_int_A": 1, "col_0_int_B": 2, "record_id_A": "x", "record_id_B": "x"}
    assert get_row_list(row) == [1, 2]

def test_get_row_list_raises_on_odd_number_of_columns():
    """An odd number of non-id columns can't be split into A/B halves."""
    row = {"a": 1, "b": 2, "c": 3, "record_id_A": "x", "record_id_B": "x"}
    with pytest.raises(ValueError):
        get_row_list(row)

def test_get_row_list_raises_on_wrong_number_of_id_columns():
    """Exactly two id columns are required to validate the row's primary key."""
    row = {"a": 1, "b": 2}
    with pytest.raises(ValueError):
        get_row_list(row)

def test_get_row_list_raises_on_mismatched_ids():
    """The two id columns in a row must refer to the same record."""
    row = {"a": 1, "b": 2, "record_id_A": "x", "record_id_B": "y"}
    with pytest.raises(ValueError):
        get_row_list(row)

def test_row2num_bits_counts_column_pairs():
    """row2num_bits should be half the number of non-id values."""
    row = {"a": 1, "b": 2, "c": 3, "d": 4, "record_id_A": "x", "record_id_B": "x"}
    assert row2num_bits(row) == 2

def test_compute_bitarray64_sets_bit_when_values_match():
    """A bit should be set when the A/B values at that position are equal."""
    row = {
        "col_0_int_A": 5, "col_1_str_A": "foo",
        "col_0_int_B": 5, "col_1_str_B": "bar",
        "record_id_A": "x", "record_id_B": "x",
    }
    # col_0 matches (bit 0 set), col_1 differs (bit 1 unset) -> 0b01
    assert compute_bitarray64(row) == 0b01

def test_count_bitarrays_counts_flipped_bits_at_position():
    """count_bitarrays should count how many bitarrays have a given bit set."""
    bitarrays = [0b01, 0b11, 0b00]
    assert count_bitarrays(bitarrays, pos=0) == 2
    assert count_bitarrays(bitarrays, pos=1) == 1

#————— Column / Row Set Operation Tests —————#

def test_column_intercept_returns_shared_columns():
    """column_intercept should return the columns common to both inputs."""
    acol = ["record_id", "col_0_int", "col_1_str"]
    bcol = ["record_id", "col_0_int", "col_2_float"]
    assert column_intercept(acol, bcol) == {"record_id", "col_0_int"}

def test_column_intercept_raises_without_id_col():
    """column_intercept requires the record id column to be shared."""
    with pytest.raises(ValueError):
        column_intercept(["a", "b"], ["a", "c"])

def test_column_symmetric_diff_reports_exclusive_columns():
    """column_symmetric_diff should report columns unique to each side."""
    acol = ["record_id", "col_0_int", "col_1_str"]
    bcol = ["record_id", "col_0_int", "col_2_float"]
    diff = column_symmetric_diff(acol, bcol)
    assert diff == {"prev_load": {"col_1_str"}, "latest_load": {"col_2_float"}}

def test_row_intercept_returns_shared_ids():
    """row_intercept should return ids present in both inputs."""
    assert row_intercept(["r1", "r2", "r3"], ["r2", "r3", "r4"]) == {"r2", "r3"}

def test_row_symmetric_diff_reports_exclusive_ids():
    """row_symmetric_diff should report ids unique to each side."""
    diff = row_symmetric_diff(["r1", "r2", "r3"], ["r2", "r3", "r4"])
    assert diff == {"prev_load": {"r1"}, "latest_load": {"r4"}}

#————— End-to-End DataFrame Tests —————#

def test_bitdiff_flags_modified_columns():
    """bitdiff should mark, per shared row, which columns changed between tables."""
    a = pl.DataFrame({"record_id": ["r1", "r2"], "col_0_int": [1, 2], "col_1_str": ["x", "y"]})
    b = pl.DataFrame({"record_id": ["r1", "r2"], "col_0_int": [1, 99], "col_1_str": ["x", "y"]})

    result = bitdiff(a, b)
    result_map = dict(zip(result["record_id"].to_list(), result["diff_bitarray"].to_list()))

    # r1: both columns match -> both bits set. r2: col_0_int differs -> bit 0 unset.
    assert result_map == {"r1": 0b11, "r2": 0b10}

def test_pruned_rows_reports_rows_unique_to_each_side():
    """pruned_rows should report ids present in only one of the two tables."""
    a = pl.DataFrame({"record_id": ["r1", "r2"]})
    b = pl.DataFrame({"record_id": ["r2", "r3"]})

    result = pruned_rows(a, b)
    sources = dict(zip(result["record_id"].to_list(), result["source_dataload"].to_list()))

    assert sources == {"r1": "previous load", "r3": "latest load"}
