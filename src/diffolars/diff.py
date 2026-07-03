import polars as pl
from datetime import datetime
from typing import Any
import numpy as np


def compute_bitarray(row: dict, id_col = 'record_id') -> int:
    """Computes the column diff bitarray in little-endian order."""
    

    # prepare lists for indexing. 
    # row_list has the non-ID column values
    row_list = [v for k, v in row.values() if id_col not in k]

    if len(row_list) % 2 != 0:
        raise ValueError(f"The number of non-ID columns must be a even \
                        so that the binary operations are correct.")

    # we use the id list to check if the input is correct
    id_list = [v for k, v in row.items() if id_col in k]

    if len(id_list) != 2:
        raise ValueError(f"Only two columns should have {id_col} in its name.")
    
    if id_list[0] != id_list[1]:
        raise ValueError(f"The two ID columns in the row dict do not match. \
                        Primary keys must match. Try presorting inputs or \
                        pruning unshared rows prior to computing bitarrays.")
    
    # Main bit array loop. We know that row_list MUST be even.
    bitarray = 0
    offset = len(row_list) / 2
    for i in range(len(row_list) / 2):
        # the idea is to mask our zero-initialized integer,
        # where the mask is the result of our boolean comparison, 
        # shifted over by i
        bitarray |= np.bitwise_left_shift((row_list[i] == row_list[i+offset]), i)
    return bitarray


def bitdiff(
    a: pl.DataFrame | pl.LazyFrame,
    b: pl.DataFrame | pl.LazyFrame,
    id_col: str = 'record_id') -> pl.DataFrame:
    """
    Given two core tables, computes a bit array that captures the differences.
    The start position maps column index 1 to the least significant bit (LSB) position.
    Column index 0 is expected to be the primary key or ID column.
    The bit array is an unsigned 64-bit integer (`pl.UInt64'), since
    `pl.UInt128` is currently unstable. 
    """
    pass
    



def get_core(
    a: pl.DataFrame | pl.LazyFrame,
    b: pl.DataFrame | pl.LazyFrame,
    id_col: str = 'record_id',
    col_sort_key = lambda x: x.split('_')[1]) -> tuple[pl.DataFrame]:
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
        a_df = a_df.filter(pl.col(id_col).is_in(ri)).select(ordered_cols)
        b_df = b_df.filter(pl.col(id_col).is_in(ri)).select(ordered_cols)

        return a_df, b_df

    except Exception as e:
        print(e)
        return pl.DataFrame()

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
    pruned_results = {'date_pruned' : datetime.now()}

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
    pruned_a = a.join(b, how="anti", on=id_col).select(
        pl.lit(datetime.now()).alias("date_pruned"),
        pl.lit("previous load").alias("source_dataload"),
        id_col
    )
    pruned_b = b.join(a, how="anti", on=id_col).select(
        pl.lit(datetime.now()).alias("date_pruned"),
        pl.lit("latest load").alias("source_dataload"),
        id_col
    )
    print(f"Found {len(pruned_a)} rows unique to the current (original) table.")
    print(f"Found {len(pruned_b)} rows unique to the next (latest) table.")
    return pl.concat([pruned_a, pruned_b], how="vertical")

    
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