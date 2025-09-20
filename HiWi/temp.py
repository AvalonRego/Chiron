import pandas as pd
path='/ptmp/arego/Record_Len_Tracks'

df=pd.read_parquet(path)
print(df.columns)