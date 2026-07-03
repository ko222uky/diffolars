# Changelog

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
