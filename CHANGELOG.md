# Changelog

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
