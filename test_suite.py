"""
Basic template for an automated unit test.
"""

# Imports
import polars as pl

#————— Functions to Check —————#

def empty_lf():
    """Dummy function that needs testing."""
    lf = pl.LazyFrame()
    # Do nothing
    return lf.collect()


#————— Test Functions —————#

# Example test we expect to succeed
def test_empty_lf():
    """Test function that tests the dummy function."""
    assert empty_lf().is_empty()

# Example test we expect to fail
def test_empty_lf_fail():
    """Test function that tests the dummy function."""
    assert not empty_lf().is_empty()