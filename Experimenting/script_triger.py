import sys
sys.path.append('../../olympus/lib/python3.10/site-packages/')
import logging
from ananke.models.collection import Collection
from ananke.configurations.collection import HDF5StorageConfiguration
logging.getLogger().setLevel(logging.INFO)
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
pd.set_option('display.max_columns', None)
import time
from joblib import Parallel, delayed

path="data/HexRealTracks.h5"

from importlib import reload
import trigger_parallel
import trigger_copy
reload(trigger_parallel)
reload(trigger_copy)
from trigger_parallel import TriggerDatasetProcessor as TDP1
from trigger_copy  import TriggerDatasetProcessor as TDP2

tdp=TDP1(path)
_=tdp.run()