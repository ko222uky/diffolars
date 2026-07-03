# Changelog

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
