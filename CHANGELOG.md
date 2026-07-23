# Changelog

## 1.1.2
- Fixed the CLI command's call to `bitdiff_plot` to properly pass the `id_col`
  to the plotting functions
- Fixed plotting functions to properly pass the `id_col` to `get_core_columns`

## 1.1.1
- Added `test_diff_cli_upset_plot_creation_respects_id_col` (`test_cli.py`),
  testing creation of the upset plot when the id column is a non-default value

## 1.1.0
- Relicensed from MIT-only to a dual MIT/Apache-2.0 license; `LICENSE` is now
  split into `LICENSE-MIT` and `LICENSE-APACHE`, and `pyproject.toml`'s
  `license` field is now the SPDX expression `MIT OR Apache-2.0`

## 1.0.9
- Fixed `get_row_list` misclassifying non-ID columns as ID columns whenever
  their name merely contained `id_col` as a substring (e.g. an
  `other_record_id_A` column alongside `record_id`), which raised a spurious
  `ValueError` about having more than two ID columns; `id_list` is now
  matched against the exact `{id_col}_A`/`{id_col}_B` column names instead of
  substring containment
- Added `test_diff_cli_id_col_substring` (`test_cli.py`), covering a table
  pair with a shared column whose name contains the ID column's name as a
  substring

## 1.0.7
- Removed unused `pandas`, `pyodbc`, `ipykernel`, `jupyter`, and `dotenv`
  dependencies, none of which are referenced anywhere in `src/`

## 1.0.6
- Renamed `demo.DEMO_COL_SORT_KEY` (a lambda) to `demo._demo_col_sort_key`,
  a plain function with a docstring, for readability

## 1.0.5
- Changed `get_core`/`get_core_columns`'s default `col_sort_key` from
  `lambda x: int(x.split('_')[1])` to `lambda x: x` (identity), since the
  former only worked for column names following the `demo.py`-generated
  naming pattern and broke the CLI pipeline on other column names
- Added `demo.DEMO_COL_SORT_KEY`, exposing the old
  `int(x.split('_')[1])` sort key for callers working with `demo.py`-style
  synthetic column names

## 1.0.4
- Fixed `report_prune`, `bitdiff`, and `bitdiff_summary` not forwarding a
  custom `id_col` down to `row_symmetric_diff`, `get_core`, and
  `get_core_columns`, so non-default primary key column names are now
  respected throughout the diff pipeline instead of silently falling back to
  `record_id`
- Fixed `get_core` not forwarding `id_col` to `column_intercept`
- Renamed `column_intercept`'s `record_id_col` parameter to `id_col` for
  consistency with the rest of the API
- Updated `diff_cli` to pass `id_col` through to `report_prune` and
  `bitdiff_summary`

## 1.0.3
- Fixed `get_df_pair` not forwarding `seed` to `get_mutated_data`, so the
  mutated frame is now reproducible alongside the original when a seed is given
- Added `test_demo.py`, unit tests for `get_df_pair` covering return shape,
  reproducibility with a fixed seed, and variation across different seeds
- Removed the `test_suite.py` placeholder/template tests now that real tests
  exist
- Added `build` and `publish` stages to `.gitlab-ci.yml`, restricted to
  `main`: `uv build` produces the package, and `uv publish` runs only if the
  `pyproject.toml` version isn't already published on PyPI (checked via new
  `check_pypi_published.py` helper script)

## 1.0.2
- Flattened the generated API reference to live under `docs/` directly
  (previously nested under `docs/api/`)
- Switched GitHub Pages docs deployment from a GitHub Actions workflow to
  branch deployment, removing `.github/workflows/pages.yml`

## 1.0.1
- Added a usage example to `diff_cli`'s docstring, demonstrating
  `get_df_pair` + `diff_cli` end-to-end
- Published the pdoc-generated API reference to GitHub Pages via a GitHub
  Actions workflow, and linked it from the README/PyPI project page

## 1.0.0
- Added `bitdiff_summary`, which reads a computed `diff_bitarray` column and
  reports per-column modified/not-modified counts across all diffed rows
- Added `bitarray_upset_plot`/`bitdiff_plot`, a hand-rolled matplotlib upset
  plot showing which columns tend to be modified together, with a `top_n`
  option to limit the plot to the most-frequently-modified categories and a
  left-hand totals histogram of single-category modification counts
- Added `matplotlib` as a dependency
- Expanded `diff_cli` with `--bitarray-summary/--no-bitarray-summary` and
  `--top-n` options, writing `bitarray_summary.parquet` and
  `bitarray_summary_upsetplot.png` alongside the existing diff outputs
- Added a `diffolars` console-script entry point for `diff_cli`, replacing
  the `python -c "from diffolars.cli import diff_cli; diff_cli()"` workaround
  with `uv run diffolars`
- Added a `pdoc`-generated API reference under `docs/api`
- First 1.0 release: the core diff pipeline (prune, core, bitdiff, summary,
  upset plot) and CLI are considered stable

## 0.5.0
- Added `diffolars.cli`, a Click-based CLI (`diff_cli`) that reads a previous
  and latest parquet dataload, runs `report_prune`, `pruned_rows`, and
  `bitdiff`, prints the three result tables, and (by default) writes them to
  `data/<prev>-<latest>/<date>/*.parquet`
- Added `click` as a dependency
- Added a guard in `compute_bitarray` raising `ValueError` when a row has more
  than 32 column pairs, since the diff bitarray is a 64-bit `UInt64`
- Truncated `date_pruned` timestamps in `report_prune`/`pruned_rows` to minute
  precision
- Swapped `get_df_pair`'s parameter order to `n_rows, n_cols` for consistency
  with the rest of the API

## 0.4.0
- Added `bitdiff`, which joins the two core tables and computes a per-row
  `diff_bitarray` (`pl.UInt64`) capturing which columns match between the
  previous and latest load
- Added bitarray helper functions (`compute_bitarray`, `brian_kernighan`,
  `count_zero_bits`, `count_unpadded_zero_bits`, `bitwise_not`,
  `get_row_list`, `row2num_bits`) supporting the bitarray diff calculation
- Changed `get_core` to also prune rows (via `row_intercept`, not just
  columns) and return a tuple of `_A`/`_B`-suffixed DataFrames instead of a
  single joined DataFrame
- Fixed `pruned_rows` logging output, which reported the "original" table's
  row count twice instead of reporting the "latest" table's count

## 0.3.1
- Fixed `get_core` to normalize `DataFrame`/`LazyFrame` inputs before joining, resolving type-checker errors from the previous mixed-type handling
- Loosened `column_symmetric_diff`, `row_intercept`, and `row_symmetric_diff` to accept `DataFrame`/`LazyFrame` inputs, matching the other set-based functions
- Widened `include_types`/`included_types` params in `demo.py` to `set[Any]`, and `report_prune`'s return type to `dict[str, Any]`, to satisfy the type checker
- Added `LazyFrame.collect()` guards in `pruned_rows` so anti-joins run against materialized data
- Removed unused `main.py` scratch script
- Various lint fixes

## 0.3.0
- Added `get_cols`/`get_row_values` helpers so set-based functions accept a `list`, `DataFrame`, or `LazyFrame` directly
- Added `get_core`, which joins two tables on their shared rows and columns to build the core comparison dataframe
- Added `prune_rows`/`report_prune` to isolate rows/columns exclusive to one table and summarize the pruning results as a loggable dict entry
- Renamed symmetric-diff dictionary keys from `original`/`mutated` to `prev_load`/`latest_load`

## 0.2.0
- Added row intersection and symmetric difference
- Added column intersection and symmetric difference; symmetric diff reports set-specific exclusives
- Added `log.py` module with a decorator for logging stdout to a file

## 0.1.0
- Initial release as `diffolars` (renamed from `yadd`)
- Demo module with `get_df_pair()`, `get_random_data()`, and `get_mutated_data()`
