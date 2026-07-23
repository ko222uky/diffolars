"""
Unit tests for the `diffolars.cli` module.

These tests focus on an edge case: `diff_cli` exposes an `--id-col` option so
callers can point it at data that doesn't use the demo module's default
"record_id" primary key column. Each test below asserts the CORRECT expected
behavior for a custom id column. As of this writing they FAIL, because
several downstream functions either don't accept an `id_col` argument at
all, or accept one but never forward it to the helpers they call internally.
Each failing test isolates one layer of that call chain (using monkeypatching
to bypass bugs in earlier layers, where needed) so the failures can be
attributed to a specific function.

Additional tests also added as edge cases are discovered for `diff_cli`.
"""

from datetime import datetime, date

import polars as pl
import os
from pathlib import Path
import diffolars.cli as cli_module
from diffolars.cli import diff_cli
import shutil

def _stub_report_prune(a, b, id_col="record_id"):
    """Stand-in for `report_prune` used to bypass its bug in other tests.

    Accepts `id_col` with a default so this stub keeps working regardless of
    whether `cli.py` calls `report_prune(o, m)` (bug present) or
    `report_prune(o, m, id_col=id_col)` (bug fixed) -- otherwise, fixing the
    real `report_prune`/`diff_cli` call signature would break these tests
    with an unrelated `TypeError` instead of letting them test what they're
    meant to test.
    """
    return {"date_pruned": datetime.now()}


def _write_pair(tmp_path, id_col):
    """Writes a minimal original/mutated parquet pair using a custom id column name."""
    # The following is an alternative test data pair in case the generated 
    # test data doesn't cover certain edge cases. Here, we can define the id_col,
    # so that it isn't the default 'record_id'. Writes results to parquet file.
    
    a = pl.DataFrame({
        id_col: ["r1", "r2", "r3"],
        "col_0_int": [1, 2, 3],
        "col_1_str": ["x", "y", "z"],
    })
    b = pl.DataFrame({
        id_col: ["r1", "r2", "r3"],
        "col_0_int": [1, 99, 3],
        "col_1_str": ["x", "y", "q"],
    })
    prev_path = tmp_path / "prev.parquet"
    latest_path = tmp_path / "latest.parquet"
    a.write_parquet(prev_path)
    b.write_parquet(latest_path)
    return prev_path, latest_path

def _write_pair_id_substring(tmp_path, id_col):
    """Writes a data pair wherein the ID col shares a substring with a non-ID col"""
    a = pl.DataFrame({
        id_col: ["r1", "r2", "r3"],
        'other_' + id_col: [1, 2, 3],
        "col_1_str": ["x", "y", "z"],
    })
    b = pl.DataFrame({
        id_col: ["r1", "r2", "r3"],
        'other_' + id_col: [1, 99, 3],
        "col_1_str": ["x", "y", "q"],
    })
    prev_path = tmp_path / "prev.parquet"
    latest_path = tmp_path / "latest.parquet"
    a.write_parquet(prev_path)
    b.write_parquet(latest_path)
    return prev_path, latest_path


def test_diff_cli_succeeds_with_default_id_col(tmp_path):
    """Sanity check: the CLI runs end-to-end when the id column is 'record_id'.

    This one is expected to PASS since it establishes that the
    pipeline works correctly, so the failures below can be attributed to the
    custom id column rather than to test setup.
    """
    prev_path, latest_path = _write_pair(tmp_path, "record_id")

    # Note: This is calling the CLI tool inline
    diff_cli(
        [
            "--no-scan",
            "--no-write",
            "--no-bitarray-summary",
            "--prev-load", str(prev_path),
            "--latest-load", str(latest_path),
            "--id-col", "record_id",
        ],
        standalone_mode=False,
    )

def test_diff_cli_id_col_substring(tmp_path):
    """Tests edge case of having columns sharing substrings with ID col"""
    prev_path, latest_path = _write_pair_id_substring(tmp_path, "record_id")
    # Note: This is calling the CLI tool inline
    diff_cli(
        [
            "--no-scan",
            "--no-write",
            "--no-bitarray-summary",
            "--prev-load", str(prev_path),
            "--latest-load", str(latest_path),
            "--id-col", "record_id",
        ],
        standalone_mode=False,
    )



def test_diff_cli_succeeds_with_non_default_id_col(tmp_path):
    """diff_cli should run without error when given a custom --id-col.

    EXPECTED TO FAIL with `polars.exceptions.ColumnNotFoundError: unable to
    find column "record_id"` since this bug was found during a real-world work scenario.

    Root cause: `diffolars.diff.report_prune` (called at cli.py's
    `report_prune(o, m)` line, before pruned_rows/bitdiff even run) has no
    `id_col` parameter at all;
     
    rather, it hardcodes 'record_id' via
    `row_symmetric_diff(a, b)`. 
    
    Needs fixing: give `report_prune` an
    `id_col` parameter (forwarded to `row_symmetric_diff`), and have
    `diff_cli` pass its `id_col` option through to `report_prune`.
    """
    prev_path, latest_path = _write_pair(tmp_path, "uid")

    diff_cli(
        [
            "--no-scan",
            "--no-write",
            "--no-bitarray-summary",
            "--prev-load", str(prev_path),
            "--latest-load", str(latest_path),
            "--id-col", "uid",
        ],
        standalone_mode=False,
    )


def test_diff_cli_bitdiff_respects_id_col(tmp_path, monkeypatch):
    """diff_cli's bitdiff step should also work with a custom --id-col.

    `report_prune` is monkeypatched to bypass the bug covered by
    `test_diff_cli_succeeds_with_non_default_id_col`, so this test can reach
    `bitdiff_df = bitdiff(o, m, id_col=id_col)` in cli.py and isolate the
    next bug...

    EXPECTED TO FAIL with `polars.exceptions.ColumnNotFoundError: unable to
    find column "uid_A"`.

    Root cause: `bitdiff` forwards its `id_col` argument to
    `get_core(a, b, id_col=id_col)`, but `get_core` itself (diff.py) then
    calls `column_intercept(a, b)` without forwarding `id_col` on to
    `column_intercept`'s `record_id_col` parameter, so `column_intercept`
    falls back to its own 'record_id' default and fails. Needs fixing:
    `get_core` must forward `id_col` as `column_intercept(a, b,
    record_id_col=id_col)`.

    Reference
    ==========

    https://docs.pytest.org/en/6.2.x/monkeypatch.html

    """
    monkeypatch.setattr(cli_module, "report_prune", _stub_report_prune)
    prev_path, latest_path = _write_pair(tmp_path, "uid")

    diff_cli(
        [
            "--no-scan",
            "--no-write",
            "--no-bitarray-summary",
            "--prev-load", str(prev_path),
            "--latest-load", str(latest_path),
            "--id-col", "uid",
        ],
        standalone_mode=False,
    )


def test_diff_cli_bitdiff_summary_respects_id_col(tmp_path, monkeypatch, capsys):
    """The bitarray summary should report real per-column modification counts
    for a custom --id-col, not silently come back empty.

    `report_prune` and `bitdiff` are monkeypatched to bypass the two bugs
    covered by other tests...

    EXPECTED TO FAIL: the summary table comes back with shape (0, 4) and no
    mention of "col_0_int"/"col_1_str", instead of a (2, 4) table showing 1
    modification for each column.

    Root cause: `bitdiff_summary` (and `bitdiff_plot`) have no `id_col`
    parameter at all -- they call `get_core_columns(a, b)` with the
    'record_id' default, which fails internally, gets swallowed by a
    try/except in `get_core`, and silently yields zero core columns.
     
    Needs fixing: give `bitdiff_summary` (and `bitdiff_plot`) an `id_col` parameter
    forwarded to `get_core_columns`, and have `diff_cli` pass its `id_col`
    option through to both calls.
    """
    # monkey patches are just a means setting any dependencies in the code
    # with a dummy temporary replacement, so we can test the actual code unit
    # that we want to test, apart from shifting dependencies or states (think of timestamps, network calls, etc)
    monkeypatch.setattr(cli_module, "report_prune", _stub_report_prune)

    def fake_bitdiff(o, m, id_col="record_id", **kwargs):
        """Monkey patch for `bitdiff` call in `diff_cli`, returning fake `bitdiff_df`"""
        return pl.DataFrame({
            id_col: ["r1", "r2", "r3"],
            "diff_bitarray": [0b11, 0b10, 0b01],
        })

    monkeypatch.setattr(cli_module, "bitdiff", fake_bitdiff)
    prev_path, latest_path = _write_pair(tmp_path, "uid")

    diff_cli(
        [
            "--no-scan",
            "--no-write",
            "--bitarray-summary",
            "--prev-load", str(prev_path),
            "--latest-load", str(latest_path),
            "--id-col", "uid",
        ],
        standalone_mode=False,
    )

    captured = capsys.readouterr()
    assert "shape: (2, 4)" in captured.out
    assert "col_0_int" in captured.out
    assert "col_1_str" in captured.out


def test_diff_cli_upset_plot_creation_respects_id_col(tmp_path, monkeypatch, capsys):
    """
    The diff cli should create the upset plot when the id column is not the default.
    The test data is created in `data/prev-latest` and is cleaned before asserting
    file existence.
    """
    monkeypatch.setattr(cli_module, "report_prune", _stub_report_prune)

    def fake_bitdiff(o, m, id_col="record_id", **kwargs):
        """Monkey patch for `bitdiff` call in `diff_cli`, returning fake `bitdiff_df`"""
        return pl.DataFrame({
            id_col: ["r1", "r2", "r3"],
            "diff_bitarray": [0b11, 0b10, 0b01],
        })

    monkeypatch.setattr(cli_module, "bitdiff", fake_bitdiff)
    prev_path, latest_path = _write_pair(tmp_path, "uid")

    data_path = Path('data', 'prev-latest', str(date.today()))
    upset_plot_path = data_path / 'bitarray_summary_upsetplot.png'  

    if os.path.exists(data_path):
        print("Cleaning old test path.")
        shutil.rmtree(data_path)

    diff_cli(
        [
            "--no-scan",
            "--write",
            "--bitarray-summary",
            "--prev-load", str(prev_path),
            "--latest-load", str(latest_path),
            "--id-col", "uid",
        ],
        standalone_mode=False,
    )

    assert os.path.exists(upset_plot_path)

    
    


