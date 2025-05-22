import os

path='/viper/ptmp/arego/LargeTracks/'

files=os.listdir(path)
files=[file for file in files if '.tmp' in file]

for file in files:
    os.remove(f'{path}{file}')