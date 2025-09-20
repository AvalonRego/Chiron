import os

path='/u/arego/Project/AssignEventNo/assign'

files=[f'{path}/{file}' for file in os.listdir(path)]

for file_name in files:
    with open(file_name, 'r') as file:
        for line in file:
            path=line.strip()
            if os.path.isfile(path):
                print(f'to remove {path}')
                os.remove(path)
