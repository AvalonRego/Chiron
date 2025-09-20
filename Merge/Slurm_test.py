import sys
import pandas as pd
import os

def main():
    # Check if there are any command-line arguments
    if len(sys.argv) < 2:
        print("No file paths provided.")
        return

    # Iterate through the provided file paths and print them
    for file_path in sys.argv[1:]:
        print(file_path)

    with pd.HDFStore(file_path, mode='a') as store:  # 'a' mode allows modifying the file
        # Read existing datasets
            hits = store['hits']
    print(hits.head())
    name = os.path.basename(file_path)

    # Define paths
    en_path = f"/viper/ptmp/arego/LargeElectrical/100000s/{name}"
    with pd.HDFStore(en_path, mode='a') as store:  # 'a' mode allows modifying the file
        # Read existing datasets
            hits = store['hits']
    print(hits.head())


    bn_path = f"/viper/ptmp/arego/LargeBio/100000s/{name}"
    print(bn_path)
    with pd.HDFStore(bn_path, mode='a') as store:  # 'a' mode allows modifying the file
        # Read existing datasets
            hits = store['hits']
    print(hits.head())

if __name__ == "__main__":
    main()
