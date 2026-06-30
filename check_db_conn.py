"""Check script for testing cloud database connection."""
from sqlalchemy import create_engine
# from sqlalchemy.pool import NullPool
from dotenv import load_dotenv
import os

import polars as pl

# Load environment variables from .env
load_dotenv()

# Fetch variables
USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

# Construct the SQLAlchemy connection string
DATABASE_URL = f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}?sslmode=require"

# Create the SQLAlchemy engine
engine = create_engine(DATABASE_URL)
# If using Transaction Pooler or Session Pooler, we want to ensure we disable SQLAlchemy client side pooling -
# https://docs.sqlalchemy.org/en/20/core/pooling.html#switching-pool-implementations
# engine = create_engine(DATABASE_URL, poolclass=NullPool)

# Test the connection
try:
    with engine.connect() as connection:
        print("Connection successful!")
except Exception as e:
    print(f"Failed to connect: {e}")


dummy_tbl = "public.dummy_data"

try:
    print(f"Writing a dummy table: {dummy_tbl}")
    # Try to insert some dummy data
    pl.DataFrame(data={
        "col1" : range(1, 101, 1),
        "col2" : range(1,1000, 10)
    }).write_database(
        table_name = dummy_tbl,
        connection=engine,
        if_table_exists="replace"
    )
    print("Done!")
except Exception as e:
    print(e)