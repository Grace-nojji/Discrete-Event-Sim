import sim_tools
from sim_tools.distributions import (
    RawContinuousEmpirical,
    GroupedContinuousEmpirical,
    RawDiscreteEmpirical,
    DiscreteEmpirical,
)

import math
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import pandas as pd
data = pd.read_csv('data(in).csv')


#dist = GroupedContinuousEmpirical(
    #lower_bounds=data['lower_bound'],
    #upper_bounds=data['upper_bound'],
    #freq = data['y'],
    #random_seed= random_seed
#)#
def make_group_dist(random_seed=None):
    data = pd.read_csv('data(in).csv')
    
    return GroupedContinuousEmpirical(
        lower_bounds=data['lower_bound'],
        upper_bounds=data['upper_bound'],
        freq=data['y'],
        random_seed=random_seed
    )


