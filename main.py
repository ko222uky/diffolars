import datadiff.diff as dd
from datadiff.demo import (
    get_random_data, get_mutated_data, get_df_pair
)

SEED = 42

def main():


    print("Getting a random original DataFrame...")
    df = get_random_data(10, 10, seed=SEED)
    print(df)
    print("Mutating data...")
    mut_df = get_mutated_data(df, seed=SEED, coverage = 0.25, n_new_cols=5, n_new_rows=5)
    print(mut_df)

    dfpair = get_df_pair(
        seed=SEED,
        n_rows=10, 
        n_cols=10,

        # for the mutated df
        n_new_rows=5,
        n_new_cols=5,
        coverage = 0.25  
    )
    print("Data Pair:\n")
    print("\nOriginal:\n")
    print(dfpair["original"])
    print("\nMutated:\n")
    print(dfpair["mutated"])


if __name__ == "__main__":
    main()