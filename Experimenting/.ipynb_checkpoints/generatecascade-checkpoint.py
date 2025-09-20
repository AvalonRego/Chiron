from ananke.configurations.detector import DetectorConfiguration
from olympus.event_generation.generators import generate
from ananke.models.collection import Collection
from ananke.schemas.event import EventType
from olympus.configuration.photon_propagation import MockPhotonPropagatorConfiguration
from olympus.event_generation.medium import MediumEstimationVariant
from olympus.configuration.generators import DatasetConfiguration, GenerationConfiguration, EventGeneratorConfiguration, UniformSpectrumConfiguration
from ananke.configurations.collection import HDF5StorageConfiguration
import os
import time
from olympus.constants import defaults
seed=defaults['seed']
modules_per_line = 20
distance_between_modules = 50.0  # m
dark_noise_rate = 16 *1e-5  # 1/ns
module_radius = 0.21  # m
pmt_efficiency = 0.42  # by Christian S.
pmt_area_radius = 75e-3 / 2.0  # m

detector = DetectorConfiguration.parse_obj(
    {
        "string": {
            "module_number": modules_per_line,
            "module_distance": distance_between_modules,
        },
        "pmt": {
            "efficiency": pmt_efficiency,
            "noise_rate": dark_noise_rate,
            "area": pmt_area_radius,
        },
        "module": {"radius": module_radius},
        "geometry": {
            "type": "single",
        },
        "geometry":{
            "type":"hexagonal",
            "number_of_strings_per_side":3,
            "distance_between_strings":80
            
        },
        "seed": 1,
    }
)

detector_configuration = detector
# This is optional
photon_propagator_configuration = MockPhotonPropagatorConfiguration(
    resolution=18000,
    medium=MediumEstimationVariant.PONE_OPTIMISTIC,
    max_memory_usage=int(2_147_483_648 / 4) # Great to overcome memory issues
)
photon_propagator_configuration.seed=1

cascade_generation_configuration = GenerationConfiguration(
    generator=EventGeneratorConfiguration(
        type=EventType.CASCADE,
        spectrum=UniformSpectrumConfiguration(
            log_minimal_energy=2,
            log_maximal_energy=5.5
        ),
        source_propagator=photon_propagator_configuration
    ),
    append=False,
    number_of_samples=15
)

def larger_dataset_gen(seed):
    path=get_unique_path(seed)
    
    storage_configuration = HDF5StorageConfiguration(
            data_path=path,
            read_only=False
    )
    detector_configuration.seed=seed
    photon_propagator_configuration.seed=seed
    
    print(detector_configuration.seed)
    print(photon_propagator_configuration.seed)
    configuration = DatasetConfiguration(
        detector=detector_configuration,
        generators=[cascade_generation_configuration],
        storage=storage_configuration
    )

    start_time=time.time()
    print(path)
    collection = generate(configuration)

    end_time=time.time()
    print(' took ',end_time-start_time)


def get_unique_path(seed):
    # Construct the initial file path
    path = f'data/LargeCascades/{seed}.h5'
    
    # Check if the file exists
    if os.path.exists(path):
        while os.path.exists(f'data/LargeCascades/{seed}.h5'):
            seed += 1
        # Update path to include the counter for uniqueness
        path = f'data/LargeCascades/{seed}.h5'
    
    return path

for i in range(1):
    larger_dataset_gen(i)