#!/bin/bash

# Define the directory containing the .h5 files
dir="Experimenting/data/LargeCascades"  # Change this to your directory path

# List all the .h5 files in the directory, extract the numeric part of their names, and sort them
existing_files=$(ls "$dir"/*.h5 | sed 's/[^0-9]*\([0-9]*\)\.h5/\1/' | sort -n)

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
file="../olympus/lib/python3.10/site-packages/olympus/constants.py"  # Change to the correct path

# Check if the Python file exists
if [ ! -f "$file" ]; then
  echo "File not found: $file"
  exit 1
fi

# Use awk to find and update the seed value in the constants.py file
awk -v seed_value="$seed" '/seed=[0-9]+/ {
    sub(/seed=[0-9]+/, "seed=" seed_value);
    print;
    next;
}
{ print }' "$file" > temp_file && mv temp_file "$file"

echo "Seed updated successfully in $file."
