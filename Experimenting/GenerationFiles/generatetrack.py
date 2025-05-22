from ananke.configurations.detector import DetectorConfiguration
from olympus.event_generation.generators import generate
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
photon_propagator_configuration.seed=seed

track_generation_configuration = GenerationConfiguration(
    generator=EventGeneratorConfiguration(
        type=EventType.REALISTIC_TRACK,
        spectrum=UniformSpectrumConfiguration(
            log_minimal_energy=2,
            log_maximal_energy=5.5
        ),
        source_propagator=photon_propagator_configuration
    ),
    append=True,
    number_of_samples=20
)

def larger_dataset_gen(seed):
    try:
        path=get_unique_path(seed)
        
        storage_configuration = HDF5StorageConfiguration(
                data_path=path,
                read_only=False
        )
        detector_configuration.seed=seed
        photon_propagator_configuration.seed=seed
        
        configuration = DatasetConfiguration(
            detector=detector_configuration,
            generators=[track_generation_configuration],
            storage=storage_configuration
        )

        start_time=time.time()
        print(path)
        generate(configuration)

        end_time=time.time()
        print(' took ',end_time-start_time)
    except Exception as e:
        print(f"An error occurred: {e}")
    
    finally:
        print('Finished execution of larger_dataset_gen.')


def get_unique_path(seed):
    # Construct the initial file path
    path = f'/u/arego/project/Experimenting/data/LargeTrack/20records/{seed}.h5'
    print(seed)
    initialseed=seed
    # Check if the file exists
    if os.path.exists(path):
        while os.path.exists(f'/u/arego/project/Experimenting/data/LargeTrack/20records/{seed}.h5'):
            seed += 1
        # Update path to include the counter for uniqueness
        path = f'/u/arego/project/Experimenting/data/LargeTrack/20records/{seed}.h5'

    print(seed)
    print(f'old seed==newseed {initialseed==seed}')
    if initialseed!=seed:
        raise ValueError("Seed already in use")

    return path

larger_dataset_gen(seed)

print('Python Script Ran')