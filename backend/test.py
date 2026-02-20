import os
from cmdstanpy import CmdStanModel

# Force MinGW
os.environ['CXX'] = 'g++'
os.environ['MAKE'] = 'mingw32-make'

# Get directory where this script lives
current_dir = os.path.dirname(os.path.abspath(__file__))

# Build absolute path to stan file inside backend
stan_path = os.path.join(current_dir, "forecast_model.stan")

print("Using Stan file:", stan_path)
print("File exists:", os.path.exists(stan_path))

model = CmdStanModel(stan_file=stan_path)