from sim_tools.distributions import (
    GroupedContinuousEmpirical,
)
import pandas as pd
import os


_dir = os.path.dirname(os.path.abspath(__file__))
data = pd.read_csv(os.path.join(_dir, "bin.csv"))

def make_group_dist(data=data, random_seed=None):
    return GroupedContinuousEmpirical(
        lower_bounds=data["lower_bound"],
        upper_bounds=data["upper_bound"],
        freq=data["y"],
        random_seed=random_seed,
    )