from ananke.configurations.detector import DetectorConfiguration
from olympus.event_generation.generators import generate
from olympus.configuration.generators import DatasetConfiguration, GenerationConfiguration, EventGeneratorConfiguration, UniformSpectrumConfiguration
from ananke.configurations.collection import HDF5StorageConfiguration
import os
import time
from olympus.constants import defaults

from olympus.configuration.generators import NoiseGeneratorConfiguration
from ananke.schemas.event import NoiseType

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
        "seed": seed,
    }
)

detector_configuration = detector
# This is optional

noise_generator_config = NoiseGeneratorConfiguration(
        type=NoiseType.ELECTRICAL,
        start_time=0,
        duration=4000,
    )
noise_generator_config.seed=seed




def larger_dataset_gen(seed):
    try:
        path=get_unique_path(seed)
        
        noise_generator_config = NoiseGeneratorConfiguration(
        type=NoiseType.ELECTRICAL,
        start_time=0,
        duration=4000,
        )

        configuration = DatasetConfiguration(
            detector=detector,
            generators=[
                GenerationConfiguration(
                    generator=noise_generator_config,
                    number_of_samples=20
                ),
            ],
            storage=HDF5StorageConfiguration(
                data_path=path,
                read_only=False
            )
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
    path = f'/raven/ptmp/arego/LargeElectrical/4000s/{seed}.h5'
    print(seed)
    initialseed=seed
    
    # Check if the file exists
    if os.path.exists(path):
        while os.path.exists(f'/raven/ptmp/arego/LargeElectrical/4000s/{seed}.h5'):
            seed += 1
        # Update path to include the counter for uniqueness
        path = f'/raven/ptmp/arego/LargeElectrical/4000s/{seed}.h5'
    
    print(seed)
    print(f'old seed==newseed {initialseed==seed}')
    if initialseed!=seed:
        raise ValueError("Seed already in use")

    return path

larger_dataset_gen(seed)