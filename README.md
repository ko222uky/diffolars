# diffolars

A small [Polars](https://pola.rs)-based toolkit for
comparing two versions of a dataframe and generating randomized test data to
exercise that comparison.

Ideally used to compare dataloads in the day-to-day of a database analyst.

## Installation

```bash
uv add diffolars
```

## Generating test data

`diffolars.demo` generates a random dataframe and a mutated copy of it, useful
for testing diff logic without hand-crafting fixtures.

```python
from diffolars.demo import get_df_pair

pair = get_df_pair(
    n_rows=100,
    n_cols=10,
    n_new_rows=5,    # rows added in the mutated copy
    n_new_cols=2,    # columns added in the mutated copy
    coverage=0.1,    # fraction of existing cells randomly changed
    seed=42,
)

original = pair["original"]
mutated = pair["mutated"]
```

Every generated row gets a `record_id` UUID column, used to match rows
between the original and mutated dataframes. `get_random_data` and
`get_mutated_data` are also available individually if you want to generate or
mutate a dataframe on its own.

## Diffing

`diffolars.diff` provides the comparison API for two dataloads (e.g. a
previous load vs. the latest load), and is under active development.

Inputs to these functions can be a `list`, `polars.DataFrame`, or
`polars.LazyFrame`.

- `column_intercept` / `column_symmetric_diff` — shared vs. exclusive columns
  between the two tables
- `row_intercept` / `row_symmetric_diff` — shared vs. exclusive rows, based on
  a record ID column
- `prune_rows` — returns the rows exclusive to each table (i.e. dropped by the
  join), tagged with which table they came from
- `report_prune` — summarizes the pruned rows/columns as a single dict entry,
  suitable for logging
- `get_core` — prunes each table down to their shared rows and columns, and
  returns them as a pair of `_A`/`_B`-suffixed DataFrames ready for a
  field-to-field comparison
- `bitdiff` — joins the two core tables and computes a per-row `diff_bitarray`
  (`pl.UInt64`), with each bit flagging whether a given column matched
  between the previous and latest load
- `bitdiff_summary` — reads back a `bitdiff` result and reports, per core
  column, how many rows were modified vs. not modified
- `bitarray_upset_plot` / `bitdiff_plot` — builds an upset plot (matplotlib)
  showing which columns tend to be modified together, with an optional
  `top_n` to limit the plot to the most-frequently-modified columns and a
  left-hand histogram of each column's total modification count

Currently only the Windows build is available.

## Command-line interface

`diffolars.cli` exposes `diff_cli`, a Click command that runs the diff
pipeline (`report_prune`, `pruned_rows`, `bitdiff`) over two parquet dataloads
and prints the three result tables. It's registered as the `diffolars`
console script.

From within this project:

```bash
uv run diffolars \
  --prev-load original.parquet \
  --latest-load mutated.parquet \
  --id-col record_id
```

Or by using `uvx`:

```bash
uvx diffolars \
  --prev-load original.parquet \
  --latest-load mutated.parquet \
  --id-col record_id
```

| Option | Default | Description |
| --- | --- | --- |
| `--prev-load` | `original.parquet` | Path to the previous/original data load. |
| `--latest-load` | `mutated.parquet` | Path to the latest/mutated data load. |
| `--id-col` | `record_id` | Name of the record identifier column. |
| `--scan` / `--no-scan` | `--scan` | Read with `pl.scan_parquet` (lazy) instead of `pl.read_parquet` (eager). |
| `--write` / `--no-write` | `--write` | Write the resulting diff tables to parquet. |
| `--bitarray-summary` / `--no-bitarray-summary` | `--bitarray-summary` | Produce a per-column modified/not-modified summary and upset plot after the bitdiff is computed. |
| `--top-n` | `20` | Limit the upset plot to the top N most-frequently-modified columns. |

When `--write` is set (the default), results are saved under
`data/<prev-stem>-<latest-stem>/<today's date>/`, as
`diff_activity_log_record.parquet`, `diff_record_differences.parquet`, and
`diff_bitarray_results.parquet`. If `--bitarray-summary` is also set, this
directory additionally gets `bitarray_summary.parquet` and
`bitarray_summary_upsetplot.png`.

## API reference

Static API docs are generated with [pdoc](https://pdoc.dev) from the
package's docstrings, and live under [docs/api](docs/api) (open
`docs/api/index.html`). Regenerate them after docstring changes with:

```bash
uv run --group dev pdoc diffolars -o docs/api
```

## License

MIT — see [LICENSE](LICENSE).
