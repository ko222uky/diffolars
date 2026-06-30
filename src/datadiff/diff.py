import polars as pl

def deduplicate(orig: pl.DataFrame, mut: pl.DataFrame) -> pl.DataFrame:
    """Given two input tables, identifies exact row-to-row matches based on a checksum."""
    pass

def row_intercept(orig: pl.DataFrame, mut: pl.DataFrame, record_id_col: str) -> list[str]:
    """Identifies shared rows, according to a specified record ID column."""
    pass

def row_symmetric_diff(orig: pl.DataFrame, mut: pl.DataFrame, record_id_col: str) -> list[str]:
    """Identifies sets of rows not shared between the two input dataframes,
    according to a specified record ID column"""
    pass

def has_same_schema(orig: pl.DataFrame, mut: pl.DataFrame) -> bool:
    """Return False if two dataframe schemas do not match."""
    pass

def parse_schema(orig: pl.DataFrame, mut: pl.DataFrame, suffix: str) -> dict[str, set[str]]:
    """
    Parses the schema of two dataframes and outputs results in the stdout.
    """
    pass

def column_intercept(orig: pl.DataFrame, mut: pl.DataFrame, suffix: str) -> set[str]:
    """
    Finds and returns the set of shared columns between two input dataframes.
    Equal columns must have the same column name and data type, excluding the suffix.
    """
    pass

def column_symmetric_diff(orig: pl.DataFrame, mut: pl.DataFrame, suffix: str) -> dict[str, set[str]]:
    """
    Finds and returns the set of different columns between two input dataframes.
    Different columns may differ by name or data type, excluding the suffix.
    """
    pass