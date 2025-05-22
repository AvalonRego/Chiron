from ananke.models.collection import Collection
from ananke.configurations.collection import MergeConfiguration
from ananke.schemas.event import RecordType
import logging
import os
import random as rn

import sys
# Configure logging to display DEBUG messages
logging.basicConfig(level=logging.INFO)

print('start')

path='/raven/u/arego/project/Experimenting/'

e_noise_files=os.listdir('/u/arego/project/Experimenting/data/LargeElectrical/100000s')
b_noise_files=os.listdir('/u/arego/project/Experimenting/data/LargeBio/100000s')

e_noise_files=[file for file in e_noise_files if '.h5' in file]
b_noise_files=[file for file in b_noise_files if '.h5' in file]
def merger(file):
    print(f'Creating {file}')
    print(f'{path}data/LargeTrack/temp/{file}')
    print(f'{path}data/LargeElectrical/100000s/{rn.choice(e_noise_files)}')
    print(f'{path}data/LargeBio/100000s/{rn.choice(b_noise_files)}')
    configuration = MergeConfiguration.parse_obj(
        {
            'in_collections': [
                {
                    'type': 'hdf5',
                    'data_path':f'{path}data/LargeTrack/20records/{file}',
                    'read_only':'False',
                },
                {
                    'type': 'hdf5',
                    'data_path': f'{path}data/LargeElectrical/100000s/{rn.choice(e_noise_files)}',
                    'read_only':'False',
                },
                {
                    'type': 'hdf5',
                    'data_path': f'{path}data/LargeBio/100000s/{rn.choice(b_noise_files)}',
                    'read_only':'False',
                },
                
            ],
            'out_collection': {
                    'type': 'hdf5',
                    'data_path': f'{path}data/LargeTMerge/20R/{file}.h5',
                    'read_only':'False',
            },
            'content': [
                {
                    'primary_type': RecordType.REALISTIC_TRACK.value,
                    'secondary_types': [RecordType.ELECTRICAL.value,RecordType.BIOLUMINESCENCE],
                    'number_of_records': 20,
                    'interval': {
                        'start': 0,
                        'end': 1000000,
                    }
                },
            ],
            
        }
    )

    Collection.from_merge(configuration)


if __name__ == "__main__":
    # Collect arguments (file paths)
    files = sys.argv[1:]
    print('start'+str(files))
    # Print each file
    for file in files:
        print(file)
        merger(file)
