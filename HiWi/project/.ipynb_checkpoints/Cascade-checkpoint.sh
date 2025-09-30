#!/bin/bash

# Specify the path to script1.sh (relative or absolute)
script1_path="Cascade_Incriment.sh"  # Adjust the relative path or use the full path

# Run the entire process 10 times
for i in {1..10}; do
    echo "Run #$i of 10"

    # Run the first Bash script (script1.sh)
    echo "Running script1.sh..."
    if [ -f "$script1_path" ]; then
        # If the file exists, run it
        bash "$script1_path"
        if [ $? -ne 0 ]; then
            echo "script1.sh failed. Exiting."
            exit 1
        fi
    else
        echo "script1.sh not found at $script1_path. Exiting."
        exit 1
    fi

    # Run the Python script (generatecascade.py) after script1.sh
    echo "Running generatecascade.py..."
    python3 generatecascade.py
    if [ $? -ne 0 ]; then
        echo "generatecascade.py failed. Exiting."
        exit 1
    fi

    echo "Run #$i completed successfully."
done

echo "All 10 runs completed successfully."

