import Trigger_Parallel_Working as tc
import pickle
import os

for i in range(25,60):
    data_path=f'LargeSMerge/{i}'
    folder=data_path.split('/')[0]
    # Run your computational task
    result = tc.run(path=f'/raven/u/arego/project/Experimenting/data/{data_path}.h5', n_workers=15)

    # Define the directory and file
    output_dir = f'/raven/u/arego/project/Experimenting/data/TriggerResult/{folder}'
    output_file = f"{i}.pkl"

    # Ensure the directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Save the result using pickle
    try:
        with open(output_dir+output_file, 'wb') as file:
            pickle.dump(result, file)
        print(f"Result successfully saved to {output_file}")
    except Exception as e:
        print(f"Error saving file: {e}")