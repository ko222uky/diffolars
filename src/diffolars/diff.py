import polars as pl
from datetime import datetime
from typing import Any, Iterable
from collections import Counter
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from pathlib import Path
########################################################
#                   BITARRAY HELPER FUNCTIONS
########################################################

def count_unpadded_zero_bits(bitarray: int) -> int:
    """Counts the zeros in a bit array."""
    # bitwise negation; shifting 1 << num_bits gives,
    # for num_bits = 4, the number 16. Subtract 1, and you
    # get 15, which is a one's mask of 4 bits = 0b1111.
    if bitarray == 0:
        return 1
    return brian_kernighan(bitwise_not(bitarray))

def bitwise_not(bitarray: int) -> int:
    """Inverts bits of a bitarray"""
    return ~ bitarray & (1 << int.bit_length(int(bitarray))) - 1

def count_zero_bits(bitarray: int, num_bits: int) -> int:
    """Uses knowledge about the number of bits needed
    for row comparisons to give the number of zeros."""
    return num_bits - brian_kernighan(bitarray)

def brian_kernighan(bitarray: int) -> int:
    """Well-known algorithm for computing number of flipped bits."""
    count = 0
    while bitarray:
        bitarray &= (bitarray -1)
        count += 1
    return count

def get_row_list(row: dict, id_col = 'record_id') -> list:
    """Prepares the row list for bit array computations"""
    # prepare lists for indexing. 
    # row_list has the non-ID column values
    row_list = [v for k, v in row.items() if id_col not in k]
    # print(row_list) # DEBUG
    if len(row_list) % 2 != 0:
        raise ValueError("The number of non-ID columns must be a even \
                        so that the binary operations are correct.")

    # we use the id list to check if the input is correct
    id_list = [v for k, v in row.items() if id_col in k]

    if len(id_list) != 2:
        raise ValueError(f"Only two columns should have {id_col} in its name.")
    
    if id_list[0] != id_list[1]:
        raise ValueError("The two ID columns in the row dict do not match. \
                        Primary keys must match. Try presorting inputs or \
                        pruning unshared rows prior to computing bitarrays.")
    return row_list

def row2num_bits(row: dict, id_col = 'record_id'):
    """The number of bits needed for a given row."""
    return len(get_row_list(row, id_col)) // 2

def compute_bitarray(row: dict, id_col = 'record_id') -> int:
    """Computes the column 64-bit diff bitarray in little-endian order."""
    
    # Main bit array loop. We know that row_list MUST be even.
    row_list = get_row_list(row, id_col)
    bitarray = 0
    offset = len(row_list) // 2

    if offset > 32:
        raise ValueError(f"The row cannot have more than 32 column pairs. \
                        Computed offset is {offset}. \
                        Expected a value <= 32.")

    for i in range(len(row_list)):
        if i+offset >= len(row_list):
            break
        bitarray |= np.bitwise_left_shift(
            (row_list[i] == row_list[i+offset]), i
        )
    return bitarray

def count_bitarrays(bitarrays: Iterable[int], pos: int) -> int:
    """Given an interable container of bitarrays, counts how many
    bits are flipped at position `pos`, in litte-endian order.
    
    The bitarray is indexed 0, so position 0 is the least significant bit.

    """
    count = 0
    mask = np.bitwise_left_shift(1, pos)
    # print(type(mask)) # DEBUG

    for bitarray in bitarrays:
        # print(bin(bitarray)) # DEBUG PRINT
        is_flipped = brian_kernighan(
            np.bitwise_and(bitarray, int(mask))
        )
        count += is_flipped
    return count

########################################################
#            DATAFRAME HELPER FUNCTIONS
########################################################

# Pruning functions / isolating differences before main bitarray calculations
def report_prune(
    a: pl.DataFrame | pl.LazyFrame, 
    b: pl.DataFrame | pl.LazyFrame,
    acol_suffix: str = '',
    bcol_suffix: str = '',
    value_for_no_exclusives: str = 'No exclusives'
    ) -> dict[str, Any]:
    """
    
    Returns a dictionary report on pruning results between two data tables.

    Columns are concatenated, but rows are not 
    since the number of different rows may be very large.
    The trimmed rows and columns are returned as a dictionary for reporting.
    This dictionary thus can be made into an entry in a logging table.
    """

    # The symm diff allows us to report the trimmed rows & cols
    csd = column_symmetric_diff(
        a, b, acol_suffix=acol_suffix, bcol_suffix=bcol_suffix
    )
    rsd = row_symmetric_diff(a, b)

    if len(csd) != 2:
        raise ValueError("The column symmetric difference dictionary results \
                         between the inputs has a length > 2. Expected 2.")
    if len(rsd) != 2:
        raise ValueError("The row symmetric difference dictionary results \
                         between the inputs has a length > 2. Expected 2.")

    # process column symm diff
    pruned_results = {'date_pruned' : datetime.now().replace(second=0, microsecond=0)}

    for (k, v1), (_, v2) in zip(csd.items(), rsd.items()):
        # these dicts share the same key
        pruned_results['cols_only_in_' + k] = ' , '.join(v1) \
            if ' , '.join(v1) else value_for_no_exclusives
        pruned_results['num_rows_only_in_' + k] = len(v2)

    return pruned_results
        
def pruned_rows(
    a: pl.DataFrame | pl.LazyFrame,
    b: pl.DataFrame | pl.LazyFrame, 
    id_col: str = 'record_id') -> pl.DataFrame:
    """Returns a DataFrame with the pruned rows."""
    if isinstance(a, pl.LazyFrame):
        a = a.collect()
    if isinstance(b, pl.LazyFrame):
        b = b.collect()

    # these are  rows in A that are not in B
    pruned_a = a.join(b, how="anti", on=id_col).select(
        pl.lit(datetime.now().replace(second=0, microsecond=0)).alias("date_pruned"),
        pl.lit("previous load").alias("source_dataload"),
        id_col
    )

    # rows in B that are not in A
    pruned_b = b.join(a, how="anti", on=id_col).select(
        pl.lit(datetime.now().replace(second=0, microsecond=0)).alias("date_pruned"),
        pl.lit("latest load").alias("source_dataload"),
        id_col
    )
    print(f"Found {len(pruned_a)} rows unique to the current (original) table.")
    print(f"Found {len(pruned_b)} rows unique to the next (latest) table.")
    return pl.concat([pruned_a, pruned_b], how="vertical")

def get_core(
    a: pl.DataFrame | pl.LazyFrame,
    b: pl.DataFrame | pl.LazyFrame,
    id_col: str = 'record_id',
    col_sort_key = lambda x: int(x.split('_')[1])) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Returns the core table, given two input data tables.
    
    The core table is what remains after pruning the rows and columns
    """
    a_df = a if isinstance(a, pl.DataFrame) else a.collect()
    b_df = b if isinstance(b, pl.DataFrame) else b.collect() 

    try:
        # columns pruned via column intercept
        # here, we're just preparing an ordered list for our select expression...
        ci = column_intercept(a, b)
        ci.remove(id_col)
        ci = list(ci)
        ci = sorted(ci, key=col_sort_key)
        # print(ci) DEBUG PRINT
        ordered_cols = []
        ordered_cols.append(id_col)
        ordered_cols.extend(ci)

        # rows pruned via row intercept
        ri = row_intercept(a_df, b_df, id_col=id_col)

        # filter & select
        a_df = (
            a_df
            .filter(pl.col(id_col)
            .is_in(ri))
            .select(ordered_cols)
            .select(pl.all().name.suffix('_A'))
        )
        b_df = (
            b_df
            .filter(pl.col(id_col)
            .is_in(ri))
            .select(ordered_cols)
            .select(pl.all().name.suffix('_B'))
        )

        return a_df, b_df

    except Exception as e:
        print(e)
        return pl.DataFrame(), pl.DataFrame()


def get_core_columns(
    a: pl.DataFrame | pl.LazyFrame,
    b: pl.DataFrame | pl.LazyFrame,
    id_col: str = 'record_id',
    col_sort_key = lambda x: int(x.split('_')[1])) -> list:
    """
    Returns the core columns, given two dataframes, excluding the record id column.
    """
    oc, _ = get_core(a, b, id_col=id_col, col_sort_key=col_sort_key)
    return [c.removesuffix('_A') for c in get_cols(oc) if id_col not in c]



# Main Column / Row Set Operation Functions

def get_cols(input: pl.DataFrame | pl.LazyFrame | list[str]) -> list[str]:
    """Given a data frame or lazy frame, returns the column list."""
    # To make things easy, handle entire df or lf inputs, too
    if isinstance(input, pl.DataFrame):
        return input.columns
    elif isinstance(input, pl.LazyFrame):
        return input.columns
    elif isinstance(input, list):
        return input
    else:
        return list()
    
def get_row_values(input: pl.DataFrame | pl.LazyFrame | list[str], col: str) -> list[str]:
    """Gets row values from a df and col name"""
    if isinstance(input, pl.DataFrame):
        return input.select(col).to_series().to_list()
    elif isinstance(input, pl.LazyFrame):
        return input.select(col).collect().to_series().to_list()
    elif isinstance(input, list):
        return input
    else:
         return list()

def column_intercept(
    acol: list[str] | pl.DataFrame | pl.LazyFrame, 
    bcol: list[str] | pl.DataFrame | pl.LazyFrame, 
    acol_suffix: str = '', bcol_suffix: str = '',
    record_id_col: str = 'record_id') -> set[str]:
    """
    Finds and returns the set of shared columns between two input dataframes.
    Equal columns must have the same column name and data type, excluding the suffix.
    """
    acol = get_cols(acol)
    bcol = get_cols(bcol)
    o = {c.replace(acol_suffix, '') for c in acol}
    m = {c.replace(bcol_suffix, '') for c in bcol}
    i = o.intersection(m)
    if record_id_col not in i:
        raise ValueError("Could not find record ID column (primary key).")
    return i

def column_symmetric_diff(
    acol: list[str] | pl.DataFrame | pl.LazyFrame,
    bcol: list[str] | pl.DataFrame | pl.LazyFrame, 
    acol_suffix: str = '', bcol_suffix: str = '') -> dict[str, set[str]]:
    """
    Finds and returns the set of different columns between two input dataframes.
    Different columns may differ by name or data type, excluding the suffix.
    """
    acol = get_cols(acol)
    bcol = get_cols(bcol)
    o = {c.replace(acol_suffix, '') for c in acol}
    m = {c.replace(bcol_suffix, '') for c in bcol}
    # symm diff --> intersection gives set-exclusive members
    osd = o.symmetric_difference(m).intersection(o)
    msd = m.symmetric_difference(o).intersection(m)
    return {
        'prev_load' :  osd,
        'latest_load'  : msd
    }

def row_intercept(
    a: list[str] | pl.DataFrame | pl.LazyFrame,
    b: list[str] | pl.DataFrame | pl.LazyFrame,
    id_col: str = "record_id") -> set[str]:
    """Identifies shared rows, given a list of primary keys or record IDs"""
    acol_id = get_row_values(a, id_col)
    bcol_id = get_row_values(b, id_col)
    o = {str(id) for id in acol_id}
    m = {str(id) for id in bcol_id}
    i = o.intersection(m) # empty sets should be checked outside.
    return i

def row_symmetric_diff(
    a: list[str] | pl.DataFrame | pl.LazyFrame,
    b: list[str] | pl.DataFrame | pl.LazyFrame,
    id_col: str = "record_id") -> dict[str, set[str]]:
    """Identifies sets of rows not shared between the two input dataframes's record ID list"""
    acol_id = get_row_values(a, id_col)
    bcol_id = get_row_values(b, id_col)
    o = {str(id) for id in acol_id}
    m = {str(id) for id in bcol_id}
    osd = o.symmetric_difference(m).intersection(o)
    msd = m.symmetric_difference(o).intersection(m)
    return {
        'prev_load' : osd,
        'latest_load'  : msd
    }

########################################################
#                   BITARRAY DIFFING FUNCTIONS
########################################################

def bitdiff(
    a: pl.DataFrame | pl.LazyFrame,
    b: pl.DataFrame | pl.LazyFrame,
    id_col: str = 'record_id',
    suffix_a: str = '_A',
    suffix_b: str = '_B',
    bitarray_col_name: str = 'diff_bitarray') -> pl.DataFrame:
    """
    Given two tables, computes a bit array that captures the differences,
    using the core tables.
    The start position maps column index 1 to the least significant bit (LSB) position.
    Column index 0 is expected to be the primary key or ID column.
    The bit array is an unsigned 64-bit integer (`pl.UInt64'), since
    `pl.UInt128` is currently unstable. 
    """
    ac, bc = get_core(a, b)
    ajb = ac.join(bc, 
        how="inner",
        left_on=id_col + suffix_a,
        right_on=id_col + suffix_b,
        coalesce=False
    )

    ajb = ajb.with_columns(
        pl.struct(pl.all())
        .map_elements(compute_bitarray, return_dtype=pl.UInt64)
        .alias("diff_bitarray")
    ).select(pl.col(id_col + suffix_a).alias(id_col), bitarray_col_name)
    return ajb

def bitdiff_summary(
    a: pl.DataFrame | pl.LazyFrame | str | Path,
    b: pl.DataFrame | pl.LazyFrame | str | Path,
    bitdiff_df: pl.DataFrame | str | Path,
    bitarray_col_name: str = 'diff_bitarray') -> pl.DataFrame:
    """
    Computes the bitdiff summary, given the bitdiff dataframe and the core column.
    Requires that the bitdiff results were already processed by the `diffolars.cli.diff_cli`
    function, with a column added named 'date_diffed'.
    """

    if isinstance(a, str) or isinstance(a, Path):
        a = pl.read_parquet(a)
    if isinstance(b, str) or isinstance(b, Path):
        b = pl.read_parquet(b)

    if not isinstance(bitdiff_df, pl.DataFrame) and \
        (isinstance(bitdiff_df, str) or isinstance(bitdiff_df, Path)):
        print("Reading bitdiff results from parquet path...")
        bitdiff_df = pl.read_parquet(bitdiff_df)

    # date processed:
    bitdiff_date = max(bitdiff_df.select('date_diffed').to_series())
    print(bitdiff_date) # DEBUG PRINT
    # Assume we have our bitdiff results from o, m...
    core_cols = get_core_columns(a, b)
    bitarrays = bitdiff_df.select(bitarray_col_name).to_series()
    # print(len(bitarrays)) # DEBUG PRINT

    # structures to hold the summary dataframe.    
    total_rows = len(bitarrays)
    bitarray_summary = {}
    cols_col = []
    cnt_not_modified_col = []
    cnt_modified_col = []

    for i, col in enumerate(core_cols):
        cnt_not_modified = count_bitarrays(bitarrays, pos=i)
        cols_col.append(col)
        cnt_not_modified_col.append(cnt_not_modified)
        cnt_modified_col.append(total_rows - cnt_not_modified)

    bitarray_summary = {
        'date_diffed' : bitdiff_date,
        'column_name' : cols_col,
        'cnt_not_modified' : cnt_not_modified_col,
        'cnt_modified' : cnt_modified_col
    }

    bitarray_summary_df = pl.from_dict(bitarray_summary)
    return bitarray_summary_df

def bitdiff_plot(
    a: pl.DataFrame | pl.LazyFrame | str | Path,
    b: pl.DataFrame | pl.LazyFrame | str | Path,
    bitdiff_df: pl.DataFrame | str | Path,
    *,
    bitarray_col_name: str = 'diff_bitarray', **kwargs) -> Figure:

    if isinstance(a, str) or isinstance(a, Path):
        a = pl.read_parquet(a)
    if isinstance(b, str) or isinstance(b, Path):
        b = pl.read_parquet(b)

    if not isinstance(bitdiff_df, pl.DataFrame) and \
        (isinstance(bitdiff_df, str) or isinstance(bitdiff_df, Path)):
        print("Reading bitdiff results from parquet path...")
        bitdiff_df = pl.read_parquet(bitdiff_df)

    core_cols = get_core_columns(a, b)
    bitarrays = bitdiff_df.select(bitarray_col_name).to_series()

    fig = bitarray_upset_plot(bitarrays=bitarrays, categories=core_cols, **kwargs)
    return fig


# Claude Code was used to generate this
# plotting function, using the following prompt:

# Suppose I have an Iterable of bitarrays, 
# in little-endian order, and a list of categories in the same index order of little-endian.
# Can you make me a function that builds an upset plot from this bitarray / column list?

# Claude: Which plotting approach should bitarray_upset_plot use?
# Me: I selected "Hand-rolled matplotlib only" to avoid relying on a niche dependency like upsetplot package
# Claude then asked which bit semantic to use. which determines set membership for the upset plot.

# Since, I want the upset plot to represent modifications, then a bit=0 should be the criteria.

# Also used the following prompt to get the left y-axis histogram with total column modification counts:

# Can you add two modifications?
# First, have an option to display only the top N categories. 
# Also, on the left-hand side of the plot, 
# we should count modifications in a single category. 
# So, for example, if column was mutated 10 times, 
# we should see that total count for that column on the left. 
# Make sense? You can also have a histogram along the left y-axis.

def bitarray_upset_plot(
    bitarrays: Iterable[int],
    categories: list[str],
    top_n: int | None = None,
    figsize: tuple[float, float] | None = None) -> Figure:
    """
    Builds an upset plot showing which columns tend to be modified together.

    `bitarrays` is an iterable of little-endian diff bitarrays as produced by
    `compute_bitarray`: a 0 bit at position i means the column named
    `categories[i]` differs between the compared rows (i.e. was modified).
    `categories` must be ordered so that index i lines up with bit i.

    If `top_n` is given, only the `top_n` categories with the highest total
    single-category modification count are kept; the remaining categories'
    bit positions are ignored entirely (both for the intersection matrix and
    the totals panel).

    A horizontal bar chart on the left shows, per category, the total number
    of rows where that single column was modified, regardless of which other
    columns were also modified in that row.

    Returns the matplotlib Figure containing the plot.
    """
    bitarrays = list(bitarrays)
    n_total = len(categories)

    # total single-category modification counts, over ALL categories
    total_counts_all = [
        sum(1 for bitarray in bitarrays if not ((bitarray >> i) & 1))
        for i in range(n_total)
    ]

    if top_n is not None and top_n < n_total:
        keep = sorted(range(n_total), key=lambda i: total_counts_all[i], reverse=True)[:top_n]
    else:
        keep = list(range(n_total))

    categories = [categories[i] for i in keep]
    total_counts = [total_counts_all[i] for i in keep]
    n = len(categories)
    empty_combo = tuple([False] * n)

    combo_counts: Counter[tuple[bool, ...]] = Counter()
    for bitarray in bitarrays:
        combo = tuple(not bool((bitarray >> i) & 1) for i in keep)
        combo_counts[combo] += 1

    combo_counts.pop(empty_combo, None)
    if not combo_counts:
        raise ValueError("No modified columns were found across the given bitarrays.")

    # sort combinations by intersection size, descending
    combos = sorted(combo_counts.items(), key=lambda kv: kv[1], reverse=True)
    combo_sizes = [size for _, size in combos]
    combo_members = [members for members, _ in combos]
    n_combos = len(combos)

    # order categories top-to-bottom by total modification count, most frequent first
    cat_order = sorted(range(n), key=lambda i: total_counts[i], reverse=True)

    # y position (top-to-bottom) for each category index, most frequent at the top
    y_of_cat = {cat_i: n - 1 - row_i for row_i, cat_i in enumerate(cat_order)}
    cat_of_y = {y: cat_i for cat_i, y in y_of_cat.items()}
    row_labels: list[str] = [categories[cat_of_y[y]] for y in range(n)]
    row_totals: list[int] = [total_counts[cat_of_y[y]] for y in range(n)]

    figsize = figsize or (max(6.0, n_combos * 0.6) + 2.0, 3 + n * 0.3)
    fig = plt.figure(figsize=figsize)
    gs = fig.add_gridspec(
        2, 2,
        width_ratios=[1, 4], height_ratios=[3, max(1, n * 0.3)],
        wspace=0.6, hspace=0.05,
    )
    ax_bar = fig.add_subplot(gs[0, 1])
    ax_matrix = fig.add_subplot(gs[1, 1], sharex=ax_bar)
    ax_totals = fig.add_subplot(gs[1, 0], sharey=ax_matrix)

    x = range(n_combos)

    # top-right: bar chart of intersection sizes
    ax_bar.bar(x, combo_sizes, color="black", width=0.6)
    for xi, size in zip(x, combo_sizes):
        ax_bar.text(xi, size, str(size), ha="center", va="bottom", fontsize=8)
    ax_bar.set_ylabel("Rows modified")
    for spine in ("top", "right"):
        ax_bar.spines[spine].set_visible(False)

    # bottom-right: dot matrix showing set membership per combination
    for y in range(n):
        if y % 2 == 0:
            ax_matrix.axhspan(y - 0.4, y + 0.4, color="0.92", zorder=0)

    for cat_i, y in y_of_cat.items():
        for xi, members in enumerate(combo_members):
            is_member = members[cat_i]
            ax_matrix.plot(
                xi, y, "o",
                color="black" if is_member else "0.85",
                markersize=8, zorder=2,
            )

    for xi, members in enumerate(combo_members):
        rows_in_combo = [y_of_cat[cat_i] for cat_i in range(n) if members[cat_i]]
        if len(rows_in_combo) > 1:
            ax_matrix.plot(
                [xi] * len(rows_in_combo), rows_in_combo,
                color="black", linewidth=1.5, zorder=1,
            )

    ax_matrix.set_yticks(range(n))
    ax_matrix.set_yticklabels(row_labels)
    ax_matrix.set_xticks([])
    ax_matrix.set_ylim(-0.5, n - 0.5)
    for spine in ("top", "right", "left", "bottom"):
        ax_matrix.spines[spine].set_visible(False)

    # bottom-left: total single-category modification counts
    ax_totals.barh(range(n), row_totals, color="black", height=0.6)
    label_pad = max(row_totals) * 0.03 if max(row_totals) > 0 else 0.1
    for y, total in enumerate(row_totals):
        ax_totals.text(
            total + label_pad, y, str(total),
            ha="right", va="center", fontsize=8, color="black",
        )
    ax_totals.invert_xaxis()
    ax_totals.set_xlabel("Total modified")
    ax_totals.set_ylim(-0.5, n - 0.5)
    ax_totals.tick_params(axis="y", left=False, labelleft=False)
    for spine in ("top", "left", "bottom"):
        ax_totals.spines[spine].set_visible(False)

    fig.suptitle("Modified-column combinations")
    plt.close(fig)
    return fig

# ojm