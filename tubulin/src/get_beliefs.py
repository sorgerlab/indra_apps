#!/usr/bin/env python
import pickle
from os import path
from argparse import ArgumentParser
from indra.belief import BeliefEngine


if __name__ == "__main__":
    description = "Set belief scores for a list or dict of statements."
    epilog = """Given a pickle file containing a list or dict of statements,
    generate belief scores for each of the statements and output a new pickle
    file containing a list of statements with beliefs. Script throws away the
    dictionaries keys. Input statements should contain evidence, otherwise
    their belief scores will be set to 0."""
    parser = ArgumentParser(description=description, epilog=epilog)

    parser.add_argument("-d", action="store_true",
                        help="set if input is a dictionary of statements")
    help_text = ("path to a pickle file containing a list or dict of"
                 "statements.")
    parser.add_argument("infile", help=help_text)
    args = parser.parse_args()
    infile = args.infile
    filename, file_extension = path.splitext(infile)
    outfile = filename + "_with_beliefs" + file_extension
    with open(args.infile, 'rb') as f:
        stmts = pickle.load(f)
    if args.d:
        stmts = [stmt for _, stmt in stmts.items()]

    # get belief scores
    for stmt in stmts:
        stmt.belief = 1
    be = BeliefEngine()
    be.set_prior_probs(stmts)

    # using pickle instead of assemble_corpus to avoid printing logging
    with open(outfile, 'wb') as f:
        pickle.dump(stmts, f)
