import os 
import time

def remove_if_old(file_path):
    """Removes the file if it was last accessed over 10 minutes ago."""
    if not os.path.exists(file_path):
        print("File does not exist.")
        return
    
    last_access_time = os.path.getatime(file_path)  # Get last access time
    current_time = time.time()  # Get current time

    if current_time - last_access_time > 600:  # 600 seconds = 10 minutes
        os.remove(file_path)

x=0

path='/viper/u/arego/Project/olympus/lib/python3.10/site-packages/'
files=os.listdir(path)
files=[file for file in files if file.endswith('.h5')]
for file in files:
    remove_if_old(f"{path}{file}")
x+=1