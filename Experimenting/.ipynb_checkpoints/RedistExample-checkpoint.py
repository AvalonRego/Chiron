import cProfile
from ananke.configurations.collection import MergeConfiguration
from ananke.models.collection import Collection
from ananke.schemas.event import RecordType
from ananke.configurations.events import EventRedistributionMode

configuration = MergeConfiguration.parse_obj(
    {
        'in_collections': [
            {
                'type': 'hdf5',
                'data_path':'data/HexCascadeBenchMark.h5',
                'read_only':'False',
            },
            {
                'type': 'hdf5',
                'data_path': 'data/Hex_electrical_noise_10_BM.h5',
                'read_only':'False',
            },
            {
                'type': 'hdf5',
                'data_path': 'data/HexBioluminescenceBenchMark.h5',
                'read_only':'False',
            },
        ],
        'out_collection': {
                'type': 'hdf5',
                'data_path': 'data/OutCollection.h5',
                'read_only':'False',
        },
        'content': [
            {
                'primary_type': RecordType.CASCADE.value,
                'secondary_types': [RecordType.ELECTRICAL.value,RecordType.BIOLUMINESCENCE],
                'number_of_records': 10,
                'interval': {
                    'start': 0,
                    'end': 1000,
                }
            },
        ],
        'redistribution': {
            'interval': {
                'start': 0,
                'end': 1000
            },
            'mode': EventRedistributionMode.CONTAINS_EVENT
        }
           
    }
)

print(configuration)

with cProfile.Profile() as profile2:
    collection=Collection.from_merge(configuration)