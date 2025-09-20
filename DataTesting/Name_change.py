import os
import time

import re

def extract_file_paths(filename):
    paths = []
    with open(filename, 'r') as file:
        for line in file:
            paths.append(line.split(":")[-1].strip())
    return paths

files=[file for file in os.listdir() if '.txt' in file]
for file in files:
    t=time.time()
    paths_list = extract_file_paths(file)
    print(len(paths_list))
    for path in paths_list:
        os.remove(path)
    print(time.time()-t)
