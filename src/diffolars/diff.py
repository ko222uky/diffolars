import polars as pl
from datetime import datetime

def report_prune(
    a: pl.DataFrame | pl.LazyFrame, 
    b: pl.DataFrame | pl.LazyFrame,
    acol_suffix: str = '',
    bcol_suffix: str = '',
    value_for_no_exclusives: str = 'No exclusives'
    ) -> dict[str, set[str]]:
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
        

def prune_rows(a: pl.DataFrame | pl.LazyFrame, b: pl.DataFrame | pl.LazyFrame, id_col: str = 'record_id') -> pl.DataFrame:
    """Returns a DataFrame with the pruned rows."""
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
    print(f"Found {len(pruned_a)} rows unique to the next (latest) table.")
    return pl.concat([pruned_a, pruned_b], how="vertical")

    



def get_cols(input: pl.DataFrame | pl.LazyFrame | list[str]) -> list[str]:
    """Given a data frame or lazy frame, returns the column list."""
    # To make things easy, handle entire df or lf inputs, too
    if isinstance(input, pl.DataFrame):
        return input.columns
    elif isinstance(input, pl.LazyFrame):
        return input.collect_schema().columns
    elif isinstance(input, list):
        return input
    else:
        return list()
    
def get_row_values(input: list[str] | pl.DataFrame | pl.LazyFrame, col: str) -> list[str]:
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
    acol: list[str], bcol: list[str], 
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

def row_intercept(a: list[str], b: list[str], id_col: str = "record_id") -> set[str]:
    """Identifies shared rows, given a list of primary keys or record IDs"""
    acol_id = get_row_values(a, id_col)
    bcol_id = get_row_values(b, id_col)
    o = {str(id) for id in acol_id}
    m = {str(id) for id in bcol_id}
    i = o.intersection(m) # empty sets should be checked outside.
    return i

def row_symmetric_diff(a: list[str], b: list[str], id_col: str = "record_id") -> dict[str, set[str]]:
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