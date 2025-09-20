import os

from ananke.configurations.collection import HDF5StorageConfiguration
from ananke.visualisation.event import draw_hit_histogram, draw_hit_distribution
from ananke.visualisation.detector import get_detector_scatter3ds
from olympus.configuration.generators import EventGeneratorConfiguration
from olympus.configuration.generators import GenerationConfiguration
from olympus.event_generation.medium import MediumEstimationVariant
from olympus.configuration.generators import UniformSpectrumConfiguration
from ananke.models.collection import Collection
from ananke.schemas.event import EventType
from olympus.configuration.photon_propagation import MockPhotonPropagatorConfiguration

from olympus.configuration.generators import DatasetConfiguration

#from ananke.configurations.presets.detector import single_line_configuration
from olympus.event_generation.generators import generate
from ananke import defaults
from ananke.configurations.detector import DetectorConfiguration

modules_per_line = 10
distance_between_modules = 50.0  # m
dark_noise_rate = 16 * 1e-5  # 1/ns
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
            "type":"grid",
            "number_of_strings_per_side":3,
            "distance_between_strings":60
            
        },
        "seed": defaults.seed,
    }
)
print(detector)

detector_configuration = detector
data_path = 'data/example/Grid_Event_Gen.h5'

storage_configuration = HDF5StorageConfiguration(
        data_path=data_path,
        read_only=False
)

# This is optional
photon_propagator_configuration = MockPhotonPropagatorConfiguration(
    resolution=18000,
    medium=MediumEstimationVariant.PONE_OPTIMISTIC,
    max_memory_usage=int(2147483648 / 32) # Great to overcome memory issues
)

cascade_generation_configuration = GenerationConfiguration(
    generator=EventGeneratorConfiguration(
        type=EventType.CASCADE,
        spectrum=UniformSpectrumConfiguration(
            log_minimal_energy=2.0,
            log_maximal_energy=5.5
        ),
        source_propagator=photon_propagator_configuration
    ),
    number_of_samples=3
)

track_generation_configuration = GenerationConfiguration(
    generator=EventGeneratorConfiguration(
        type=EventType.REALISTIC_TRACK,
        spectrum=UniformSpectrumConfiguration(
            log_minimal_energy=2.0,
            log_maximal_energy=5.5
        ),
        source_propagator=photon_propagator_configuration
    ),
    append=True, # Important as otherwise no extra records are generated
    number_of_samples=3
)

starting_track_generation_configuration = GenerationConfiguration(
    generator=EventGeneratorConfiguration(
        type=EventType.STARTING_TRACK,
        spectrum=UniformSpectrumConfiguration(
            log_minimal_energy=2.0,
            log_maximal_energy=5.5
        ),
        source_propagator=photon_propagator_configuration
    ),
    append=True,
    number_of_samples=3
)
configuration = DatasetConfiguration(
    detector=detector_configuration,
    generators=[
        cascade_generation_configuration,
        track_generation_configuration,
        starting_track_generation_configuration,
    ],
    storage=storage_configuration
)
try:
    os.remove(data_path)
except OSError:
    pass

collection = generate(configuration)