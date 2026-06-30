"""
The `demo` module provides functions 
to generate a random initial `polars.DataFrame`
and a mutated copy.
"""

import itertools
import random
import string
import uuid
from datetime import datetime, timedelta

import polars as pl

# The default include types;
# the randomized data is guaranteed to include a column 
# with these data types. Note that the data types require
# their own generators.
DEFAULT_INCLUDE_TYPES = {int, float, str, datetime}

# lambda functions for generating random values
_GENERATORS = {
    int: lambda rng: rng.randint(-1_000_000, 1_000_000),
    float: lambda rng: rng.uniform(-1_000_000.0, 1_000_000.0),
    str: lambda rng: "".join(rng.choices(string.ascii_letters, k=10)),
    datetime: lambda rng: datetime(2000, 1, 1)
    + timedelta(seconds=rng.randint(0, 60 * 60 * 24 * 365 * 25)),
}

# lambda functions for mutatin an existing value, keeping its type.
# to keep things simple, all of the operators are '+'
_MUTATORS = {
    int: lambda rng, v: v + rng.randint(-1_000, 1_000),
    float: lambda rng, v: v + rng.uniform(-1_000.0, 1_000.0),
    str: lambda rng, v: v + "".join(rng.choices(string.ascii_letters, k=5)),
    datetime: lambda rng, v: v + timedelta(seconds=rng.randint(-100_000, 100_000)),
}

# generates a random data frame
def get_random_data(
    n_rows: int,
    n_cols: int,
    include_types: set[type] = DEFAULT_INCLUDE_TYPES,
    seed: int | None = None,
) -> pl.DataFrame:
    """Generate a random Polars dataframe of test data.

    Every row gets a "record_id" uuid column in addition to the n_cols
    generated columns. include_types is cycled across the columns, so
    n_cols must be at least len(include_types).

    The order of operations is:

        (1) Mutate existing table cells
        (2) Add new rows
        (3) Add new columns

    Parameters
    ==========

        n_rows: number of rows to generate.

        n_cols: number of generated columns (not counting "record_id").
            Must be >= len(include_types).

        include_types: set of types to cycle through when naming and
            generating columns.

        seed: optional seed for reproducible output.

    Returns
    =======

        Randomly generated `polars.DataFrame`
    """

    # check if any unsupported types were passed;
    unsupported = include_types - _GENERATORS.keys()

    if unsupported:
        raise ValueError(f"Unsupported types in include_types: {unsupported}")
    
    # cannot specify fewer columns than number of specified included types.
    if n_cols < len(include_types):
        raise ValueError(
            f"n_cols ({n_cols}) must be >= number of include_types ({len(include_types)})"
        )

    # set the seed and initialize the types as an ordered list...
    rng = random.Random(seed)
    types = list(include_types)

    # prepare the record_id column.
    data = {"record_id": [str(uuid.uuid4()) for _ in range(n_rows)]}


    for col_idx in range(n_cols):
        
        # we mod the index by the type length, so that adding additional columns
        col_type = types[col_idx % len(types)]

        # get the random generator for our new column 
        gen = _GENERATORS[col_type]

        # add it to our data dict
        data[f"col_{col_idx}_{col_type.__name__}"] = [gen(rng) for _ in range(n_rows)]

    return pl.DataFrame(data)

def get_mutated_data(
    original_df: pl.DataFrame,
    coverage: float = 0.1, # this is the the % of the N x N data matrix that gets mutated.
    n_new_rows: int = 0,
    n_new_cols: int = 0,
    include_types: set[type] = DEFAULT_INCLUDE_TYPES,
    seed: int | None = None,
) -> pl.DataFrame:
    """
    Given an input `polars.DataFrame`, returns a mutated version.

    The mutated version may include additional columns and rows,
    along with randomly mutated fields in the data matrix.

    Parameters
    ==========
    
        coverage: fraction (0.0-1.0) of existing data cells (every column
            except "record_id") that get randomly nudged in place, e.g. a
            number gets added to, a string gets concatenated, a datetime gets
            shifted.
    
        n_new_rows: number of additional randomly generated rows to append,
            each with its own new "record_id".
    
        n_new_cols: number of additional randomly generated columns to
            append, cycling through `include_types` the same way as
            `get_random_data`.

    Returns
    ========

        Mutated `polars.DataFrame`
    """

    # check user input for the data coverage. Must be in range [0,1]
    if not 0.0 <= coverage <= 1.0:
        raise ValueError(f"coverage ({coverage}) must be between 0.0 and 1.0")

    # again, set seed.
    rng = random.Random(seed)

    # get all of the data columns (except the record_id)
    data_cols = [c for c in original_df.columns if c != "record_id"]
    n_rows = original_df.height

    # pull out the data as data dict so individual cells can be
    # mutated and rows/columns appended without rebuilding the frame each time...
    data = original_df.to_dict(as_series=False)

    # mutate a random sample of (row, column) cells in place, matching the
    # mutator to whatever type the existing value already is.
    # We get a Cartesian product of row indices and columns! this is like getting our [i, j] pairs...
    cells = list(itertools.product(range(n_rows), data_cols))
    n_mutate = round(coverage * len(cells))

    # we sample a random (row, column) for n_mutate times...
    for row_idx, col_name in rng.sample(cells, n_mutate):
        value = data[col_name][row_idx]
        mutate = _MUTATORS[type(value)] # Remember: mutate is our lambda function that takes rng, v
        data[col_name][row_idx] = mutate(rng, value)

    # append n_new_rows, generated the same way as get_random_data, reusing
    # each existing column's data type.
    if n_new_rows > 0:
        if n_rows == 0:
            raise ValueError("cannot add rows: original_df has no rows to infer column types from")
        
        # original data record_id extens to include id's for our n_new_rows...
        data["record_id"].extend(str(uuid.uuid4()) for _ in range(n_new_rows))

        # again, for each colum in the original input, we generate data to cover the new rows.
        for col_name in data_cols:
            gen = _GENERATORS[type(data[col_name][0])]

            # data is extended...
            data[col_name].extend(gen(rng) for _ in range(n_new_rows))


    total_rows = n_rows + n_new_rows

    # append n_new_cols, cycling through include_types as in get_random_data.
    if n_new_cols > 0:

        # same check for supported types
        unsupported = include_types - _GENERATORS.keys()

        if unsupported:
            raise ValueError(f"Unsupported types in include_types: {unsupported}")
        
        types = list(include_types)
        
        # offset since we're horizontally appending these new columns 
        for offset in range(n_new_cols):
            col_type = types[offset % len(types)]
            gen = _GENERATORS[col_type]
            col_idx = len(data_cols) + offset # computed col index

            data[f"col_{col_idx}_{col_type.__name__}"] = [
                gen(rng) for _ in range(total_rows)
            ]

    return pl.DataFrame(data)

def get_df_pair(
    n_cols: int,
    n_rows: int, 
    *,
    n_new_rows: int = 0,
    n_new_cols: int = 0,
    seed: int | None = None,
    included_types: set[int, float, str, datetime] = DEFAULT_INCLUDE_TYPES, 
    coverage: float = 0.1) -> dict[str, pl.DataFrame]:
    """Prepares a pair of original and mutated `polars.DataFrame`'s."""
    print(f"Generating initial dataset with {n_rows} rows and {n_cols} columns.")
    df = get_random_data(n_rows=n_rows, n_cols=n_cols, include_types=included_types, seed=seed)
    mut_df = get_mutated_data(
        df, coverage=coverage, n_new_rows = n_new_rows, n_new_cols = n_new_cols,
        include_types=included_types)
    print("Generated mutated dataset.")
    return {
        'original' : df,
        'mutated'  : mut_df
    }
