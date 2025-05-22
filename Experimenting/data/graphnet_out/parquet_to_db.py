import sys
sys.path.append('/u/arego/project/Experimenting/')

import Trigger_Improve as ti
import time


import pandas as pd
import sqlite3
import os

c=ti.initialize_collection('/u/arego/project/Experimenting/data/LargeCMerge/1.h5')

with c:
    h=c.storage.get_hits()
    r=c.storage.get_records()
    d=c.storage.get_detector()

th=h.df[['time', 'string_id', 'module_id', 'pmt_id', 'record_id']]

t=time.time()
mh=pd.merge(th,d.df,on=['string_id', 'module_id', 'pmt_id'],how='inner')
print(time.time()-t)

mh.rename(columns={'record_id':'event_no'},inplace=True)
cols=[c for c in mh.columns if 'string' not in c]
mh=mh[cols]

r.df.rename(columns={'record_id':'event_no'},inplace=True)
print(r.df.columns)


# Sample data for demonstration

# Path to the SQLite database
db_path = "/u/arego/project/Experimenting/data/graphnet_out/HandmadeDB/merged.db"

# Ensure the output directory exists
output_dir = os.path.dirname(db_path)
os.makedirs(output_dir, exist_ok=True)

# Connect to the SQLite database (this will create the database file if it doesn't exist)
conn = sqlite3.connect(db_path)

# Write DataFrames to tables in the SQLite database
r.df.to_sql("truth", conn, if_exists="replace", index=False)  # Save df1 as 'table1'
mh.to_sql("hits", conn, if_exists="replace", index=False)  # Save df2 as 'table2'

# Verify tables in the database
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Tables in the database:", [table[0] for table in tables])

# Close the connection
conn.close()
print(f"Database saved at {db_path}")
