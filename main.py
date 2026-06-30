import datadiff.demo as ddd

def main():
    seed = 42

    print("Getting a random original DataFrame...")
    df = ddd.get_random_data(10, 10, seed=42)
    print(df)
    print("Mutating data...")
    mut_df = ddd.get_mutated_data(df, coverage=0.25, n_new_cols=10, n_new_rows=10, seed=42)
    print(mut_df)


if __name__ == "__main__":
    main()