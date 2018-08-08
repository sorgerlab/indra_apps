import pandas as pd
import numpy as np
import networkx as nx
import pickle

with open("../input/july_2018_pa_directed_agg_HGNC_FPLX.pkl", "rb") as f:
    network = pickle.load(f)

with open("../input/evidence_counts.pkl", "rb") as f:
    evidence_counts = pickle.load(f)


def fermi_confidence(num_statements):
    """Get a confidence score that a relation is real from the number of
    statements in the database that assert the relation. Fermi estimate
    cooked up with an improper linear model that uses no training data."""
    if num_statements == 0:
        return 0
    else:
        return 1/(1 + num_statements**-np.log(3))
    
output = []
for key, interaction in network.items():
    # Exclude Complexes
    if interaction["type"] == "Complex":
        continue
    # some agent tuples have SUBJECT first, others have OBJECT
    # normalize by sorting
    hash = key
    agents = sorted(interaction["agents"],
                    key=lambda x: x[1])
    subj = agents[1][3] + ":::" + agents[1][4]
    obj = agents[0][3] + ":::" + agents[0][4]
    # If the interaction is not in the evidence counts dictionary, be
    # conservative and set its evidence count to 1
    try:
        evidence_count = evidence_counts[hash]
    except KeyError:
        evidence_count = 1
    confidence = fermi_confidence(evidence_count)
    directed = "D"
    type_ = interaction["type"]

    output.append([subj, obj, confidence, directed])

interactome = pd.DataFrame(output, columns=["Subject", "Object",
                                            "Confidence", "Type"])

interactome.to_csv("../work/directed_interactome.tsv", sep="\t", header=False, index=False)
    
