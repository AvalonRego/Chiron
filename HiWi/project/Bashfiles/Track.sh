#!/bin/bash

# Path to the first Bash script (Track_Inc.sh)
script1_path="/u/arego/project/Bashfiles/Track_Inc.sh"  # Update with the correct path if needed

# Path to the Python script directory
python_script_dir="/u/arego/project/Experimenting/GenerationFiles"  # Directory where your Python scripts are located

# Manual step: Set the Python script you want to run here
python_script="generatetrack.py"  # Set the name of your Python script here (e.g., generatetrack.py, another_script.py)

total_runs=20

# Run the process for the specified number of iterations
for (( i=1; i<=total_runs; i++ )); do
    echo "Starting run #$i of $total_runs"

    # Step 1: Run the first Bash script (Track_Inc.sh)
    echo "Running Track_Inc.sh..."
    if [ -f "$script1_path" ]; then
        bash "$script1_path"
        if [ $? -ne 0 ]; then
            echo "Warning: Track_Inc.sh failed during run #$i. Skipping to the next iteration."
            continue  # Skip to the next iteration
        fi
    else
        echo "Error: Track_Inc.sh not found. Stopping the process."
        exit 1
    fi

    # Step 2: Run the manually specified Python script
    echo "Running Python script: $python_script..."
    python_script_path="$python_script_dir/$python_script"

    if [ -f "$python_script_path" ]; then
        python3 "$python_script_path"
        if [ $? -ne 0 ]; then
            echo "Warning: $python_script failed during run #$i. Skipping to the next iteration."
            continue  # Skip to the next iteration
        fi
    else
        echo "Error: $python_script not found in $python_script_dir. Stopping the process."
        exit 1
    fi

    echo "Run #$i completed successfully."
done

# Final message after all runs are complete
echo "All $total_runs runs attempted. Check logs for any skipped iterations."
