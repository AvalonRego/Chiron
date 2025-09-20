# Chiron

This is the full pipeline created for :
- Simulating Neutrino Event
- Cleaning and testing for corrupted datasets
- Merging the Neutrino Event dataset with Bioluminescent and Electrical Noise
- Redistributing the Events inside the noise
- Assigning Event Numbers for Machine Learning with Graphnet (link to my other git here)

## Installation on Raven or Viper
```bash
#load modules for Raven
module load anaconda/3/2023.03 cuda/12.1 jax/0.4.1 cudnn/8.9.0 gcc/11 

#load modules for viper
module load anaconda/3/2023.03 gcc/13

python3 -m venv olympus

. olympus/bin/activate

pip install -r requrments.txt #available in the files above

pip install git+https://github.com/cescalara/PROPOSAL.git@fix-lib-load

pip install git+https://github.com/pone-software/ananke.git@main

pip install git+https://github.com/cescalara/olympus.git@test-propagation
