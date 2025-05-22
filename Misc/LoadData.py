import pandas as pd
import os

paths=[
    '/u/arego/Project/LargeCascades/20records',
    '/u/arego/Project/LargeElectrical/100000s',
    '/u/arego/Project/LargeBio',
]


for path in paths:
    file=os.listdir(path)[110]
    file_path=f'{path}/{file}'
    with pd.HDFStore(file_path, mode='a') as store:  # 'a' mode allows modifying the file
            # Read existing datasets
                hits = store['hits']
                print(hits)
                
