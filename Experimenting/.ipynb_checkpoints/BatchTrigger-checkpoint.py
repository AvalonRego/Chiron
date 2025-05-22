import Trigger_Parallel_Working as tc
import pickle

# Setup logging
tc.setup_logging('run_log.log')

# Run your computational task
result = tc.run(path='/raven/u/arego/project/Experimenting/data/LargeTrack/0.h5', n_workers=8)

# Save the result using pickle
with open('/raven/u/arego/project/data/Experimenting/TriggerResult/1000sR.pkl', 'wb') as file: 
    pickle.dump(result, file)
