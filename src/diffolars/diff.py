import polars as pl

def deduplicate(orig: pl.DataFrame, mut: pl.DataFrame) -> pl.DataFrame:
    """Given two input tables, identifies exact row-to-row matches based on a checksum."""
    pass

def has_same_schema(orig: pl.DataFrame, mut: pl.DataFrame) -> bool:
    """Return False if two dataframe schemas do not match."""
    pass

def parse_schema(orig: pl.DataFrame, mut: pl.DataFrame, suffix: str) -> dict[str, set[str]]:
    """
    Parses the schema of two dataframes and outputs results in the stdout.
    """
    pass


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
        'original' : osd,
        'mutated'  : msd
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
        'original' : osd,
        'mutated'  : msd
    }