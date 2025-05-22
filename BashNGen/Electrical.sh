#!/bin/bash

# Path to the first Bash script (Cascade_Inc.sh)
script1_path="/u/arego/Project/BashNGen/Electrical_Inc.sh"  # Update with the correct path if needed

# Path to the Python script directory
python_script_dir="/u/arego/Project/BashNGen"  # Directory where your Python scripts are located

# Manual step: Set the Python script you want to run here
# Example: python_script="generatecascade.py"
# Change this variable to the name of the Python script you want to run for each iteration.
python_script="ElectricalScript.py"  # Set the name of your Python script here (e.g., generatecascade.py, another_script.py)

total_runs=400

# Run the process 10 times
for (( i=1; i<=total_runs; i++ )); do
    echo "Starting run #$i of $total_runs"

    # Step 1: Run the first Bash script (Electrical_Inc.sh)
    echo "Running Electrical_Inc.sh..."
    if [ -f "$script1_path" ]; then
        bash "$script1_path"
        if [ $? -ne 0 ]; then
            echo "Warning: Electrical_Inc.sh failed, but continuing to the next step."
        fi
    else
        echo "Error: Electrical_Inc.sh not found. Stopping the process."
        exit 1
    fi

    # Step 2: Run the manually specified Python script
    echo "Running Python script: $python_script..."
    python_script_path="$python_script_dir/$python_script"

    if [ -f "$python_script_path" ]; then
        python3 "$python_script_path"
        if [ $? -ne 0 ]; then
            echo "Warning: $python_script encountered an error, but continuing to the next iteration."
            continue  # Move to the next iteration instead of stopping the script
        fi
    else
        echo "Error: $python_script not found in $python_script_dir. Stopping the process."
        exit 1
    fi

    echo "Run #$i completed successfully."
done

# Final message after all runs are complete
echo "All $total_runs runs completed successfully."

