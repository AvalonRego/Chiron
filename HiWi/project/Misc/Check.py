import os

path='/viper/ptmp/arego/'
#path='/u/arego/Project/LargeTrack/20records'
files=os.listdir(path)
#files=[file for file in files if '.h5' in file]
print((files))
for file in files:
    files1=os.listdir(path+file)
    if len(files1)>3:
        print(f'{file} : has {len(files1)} files')
    else:
        for file1 in files1:
            if '.h5' in file1:
                continue
            files2=os.listdir(f'{path}{file}/{file1}')
            if len(files2)>3:
                print(f'{file}/{file1} : has {len(files2)} files')


#print(no)