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

`diffolars.diff` will define the comparison API (row/column intersection and
symmetric difference, schema comparison) and is under active development...

Currently only the Windows build is available.

## License

MIT — see [LICENSE](LICENSE).
