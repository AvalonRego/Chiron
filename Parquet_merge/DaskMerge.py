import dask.dataframe as dd
import glob
from dask.diagnostics import ProgressBar

# Enable Dask's progress bar globally
ProgressBar().register()

# Path to all Parquet files
parquet_files_hits = glob.glob("/viper/ptmp/arego/LBC_parquet/hits/*.parquet")
parquet_files_records = glob.glob("/viper/ptmp/arego/LBC_parquet/records/*.parquet")

# Process "hits" files
print("Processing 'hits' Parquet files...")
df_hits = dd.read_parquet(parquet_files_hits, engine="pyarrow")
df_hits.to_parquet("/viper/ptmp/arego/LBC_parquet/hits/merged/merged_dataset.parquet", engine="pyarrow", write_index=False)

# Process "records" files
print("Processing 'records' Parquet files...")
df_records = dd.read_parquet(parquet_files_records, engine="pyarrow")
df_records.to_parquet("/viper/ptmp/arego/LBC_parquet/records/merged/merged_dataset.parquet", engine="pyarrow", write_index=False)

print("Merging completed successfully!")
