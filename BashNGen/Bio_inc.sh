#!/bin/bash

# Define the directory containing the .h5 files
dir="/viper/ptmp/arego/LargeBio/4000s/"  # Change this to your directory path

if [ ! -d "$dir" ]; then
  echo "Directory not found: $dir"
  echo "Creating directory: $dir"
  mkdir -p "$dir"  # Creates the directory, and -p avoids errors if the directory already exists
  if [ $? -eq 0 ]; then
    echo "Directory created successfully: $dir"
  else
    echo "Failed to create directory: $dir"
    exit 1
  fi
fi
# List all the .h5 files in the directory, extract the numeric part of their names, and sort them
# Define the maximum length for the numeric part
max_length=70

existing_files=$(ls "$dir"/*.h5 2>/dev/null | \
                 awk -v max_len="$max_length" 'length($0) <= max_len' | \
                 sed 's/.*\/\([0-9]*\)\.h5/\1/' | \
                 sort -n)
# Check if any .h5 files were found
if [ -z "$existing_files" ]; then
  echo "No .h5 files found in $dir."
fi

# Find the smallest missing number (seed)
seed=0
for num in $existing_files; do
  if [ "$num" -eq "$seed" ]; then
    seed=$((seed + 1))
  else
    break
  fi
done

# Output the chosen seed
echo "The next seed to use is: $seed"

# Path to the Python file containing the seed variable
file="/u/arego/Project/olympus/lib/python3.10/site-packages/olympus/constants.py" 

# Check if the Python file exists
if [ ! -f "$file" ]; then
  echo "File not found: $file"
  exit 1
fi

# Check if the file is empty
if [ ! -s "$file" ]; then
    # Copy contents from source_file.py to the constants.py file
    cp /u/arego/Project/olympus/lib/python3.10/site-packages/olympus/constants_copy.py "$file"
    echo "Copied contents from source_file.py to $file."
fi

# Use awk to find and update the seed value in the constants.py file
awk -v seed_value="$seed" '/seed=[0-9]+/ {
    sub(/seed=[0-9]+/, "seed=" seed_value);
    print;
    next;
}
{ print }' "$file" > temp_file && mv temp_file "$file"

echo "Seed updated successfully in $file."

