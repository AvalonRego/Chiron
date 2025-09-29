# Chiron

This is the full pipeline created for :
- Simulating Neutrino Event
- Cleaning and testing for corrupted datasets
- Merging the Neutrino Event dataset with Bioluminescent and Electrical Noise
- Redistributing the Events inside the noise
- Assigning Event Numbers for Machine Learning with [Graphnet](https://github.com/AvalonRego/graphnet) 
## Installation on Raven or Viper

Clone and cd into the Repo
```bash
#load modules for Raven
module load anaconda/3/2023.03 cuda/12.1 jax/0.4.1 cudnn/8.9.0 gcc/11 

#load modules for viper
module load anaconda/3/2023.03 gcc/13

python3 -m venv olympus

. olympus/bin/activate

pip install -r requrments.txt 

pip install git+https://github.com/cescalara/PROPOSAL.git@fix-lib-load

pip install git+https://github.com/pone-software/ananke.git@main

pip install git+https://github.com/cescalara/olympus.git@test-propagation

```
Also check [Olympus](https://github.com/pone-software/olympus) and [Ananke](https://github.com/pone-software/ananke)

#Notes on directories
- BashNGen
  - Run *_slurm.sh to run the default simpulations
-- modify the python script to change the energy range and number of records simulated in one go.
-- modify the [event_type].sh file to change the number of files to be generated.
