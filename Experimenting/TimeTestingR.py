from ananke.configurations.collection import HDF5StorageConfiguration
from olympus.configuration.generators import EventGeneratorConfiguration
from olympus.configuration.generators import GenerationConfiguration
from olympus.event_generation.medium import MediumEstimationVariant
from olympus.configuration.generators import UniformSpectrumConfiguration
from ananke.schemas.event import EventType
from olympus.configuration.photon_propagation import (
    MockPhotonPropagatorConfiguration,
)
from ananke.configurations.detector import DetectorConfiguration
from olympus.configuration.generators import DatasetConfiguration
from olympus.event_generation.generators import generate

import time
import numpy as np

import os

os.environ["XLA_PYTHON_CLIENT_PREALLOCATE"] = "false"  # add this
os.environ["XLA_PYTHON_CLIENT_ALLOCATOR"] = "\"platform\""

import jax

# Global flag to set a specific platform, must be used at startup.
jax.config.update('jax_platform_name', 'cpu')

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

times=np.array([])
sample=np.array([])
for i in range(1,2):
    samples=10
    photon_propagator_configuration = MockPhotonPropagatorConfiguration(
        resolution=18000,
        medium=MediumEstimationVariant.PONE_OPTIMISTIC,
        max_memory_usage=int(2147483648 / 4)
    )                       

    configuration = DatasetConfiguration(
        detector=detector,
        generators=[
            GenerationConfiguration(
                generator=EventGeneratorConfiguration(
                    type=EventType.REALISTIC_TRACK,
                    spectrum=UniformSpectrumConfiguration(
                        log_minimal_energy=2.0,
                        log_maximal_energy=5.5
                    ),
                    source_propagator=photon_propagator_configuration
                ),
                number_of_samples=samples
            )
        ],
        storage=HDF5StorageConfiguration(
            data_path=f'Experimenting/data/timetestR/{samples}_{time.time()}.h5',
            read_only=False
        )
    )

    start_time=time.time()
    print(samples)
    collection = generate(configuration)
    end_time=time.time()-start_time
    times=np.append(times,end_time)
    sample=np.append(sample,samples)
    print(times)
    print(sample)

