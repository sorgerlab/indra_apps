import pandas as pd
import numpy as np
import networkx as nx
import pickle

with open('../input/july_2018_pa_directed_agg_HGNC_FPLX.pkl', 'rb') as f:
    interactome = pickle.load(f)


for key, interaction in interactome.items():
    # Exclude Complexes
    if interaction[1]['type'] = 
