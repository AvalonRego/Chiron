import os

files=['Red_T_7K',
       'Red_T_7K_1',
       'Red_T_7K_1_1',
       'Red_T_7K_1_EN_100'
        ]

main_path='/ptmp/arego/'

for file in files:
    h5_files=[f'{main_path}{file}/{f}' for f in os.listdir(f'{main_path}{file}')]
    print(len(h5_files))
    for f in h5_files:
        fid=os.path.basename(f)
        file_id=fid.split('.')[0]
        try:
            file_id=int(file_id)
        except:
            print(f)
            if os.path.isfile(f):
                os.remove(f)

