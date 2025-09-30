#!/bin/bash

# Define the source files
cascade_sh="Cascade.sh"
cascade_inc_sh="Cascade_Inc.sh"

# Define the corresponding target files
target_sh_files=("Bio.sh" "Cascade.sh" "Electrical.sh" "Starting.sh" "Track.sh")
target_inc_files=("Bio_inc.sh" "Cascade_Inc.sh" "Electrical_Inc.sh" "Starting_Inc.sh" "Track_Inc.sh")

# Loop through each target .sh file and copy Cascade.sh content into it
for file in "${target_sh_files[@]}"; do
    echo "Copying contents of $cascade_sh to $file..."
    cp "$cascade_sh" "$file"
done

# Loop through each target .inc.sh file and copy Cascade_Inc.sh content into it
for file in "${target_inc_files[@]}"; do
    echo "Copying contents of $cascade_inc_sh to $file..."
    cp "$cascade_inc_sh" "$file"
done

echo "Files updated successfully!"
