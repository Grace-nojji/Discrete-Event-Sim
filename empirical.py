from sim_tools.distributions import (
    GroupedContinuousEmpirical,
)
import pandas as pd

data = pd.read_csv("data(in).csv")


def make_group_dist(random_seed=None):
    data = pd.read_csv("data(in).csv")
    return GroupedContinuousEmpirical(
        lower_bounds=data["lower_bound"],
        upper_bounds=data["upper_bound"],
        freq=data["y"],
        random_seed=random_seed,
    )
