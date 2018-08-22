#!/usr/bin/env python

import pickle
from indra.belief import BeliefEngine

stmts = "../work/stmts_combined.pkl"
outfile = "../work/stmts_with_beliefs.pkl"


if __name__ == "__main__":
    with open(stmts, 'rb') as f:
        stmts_dict = pickle.load(f)
    stmts = [stmt for _, stmt in stmts_dict.items()]

    # get belief scores
    for stmt in stmts:
        stmt.belief = 1
    be = BeliefEngine()
    be.set_prior_probs(stmts)

    stmts_dict = dict(zip([hash_ for hash_, _ in stmts_dict.items()],
                          stmts))

    # using pickle instead of assemble_corpus to avoid printing logging
    with open(outfile, 'wb') as f:
        pickle.dump(stmts_dict, f)
