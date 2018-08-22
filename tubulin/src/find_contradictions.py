#!/usr/bin/env python3
import pickle
from argparse import ArgumentParser
from os import path
from indra.preassembler import Preassembler
from indra.preassembler.hierarchy_manager import hierarchies


if __name__ == "__main__":
    description = ("find pairs of contradicting statements within a list "
                   "of statements")
    epilog = ("creates a pickle file containing a list of pairs of"
              "contradicting statements.")
    parser = ArgumentParser(description=description, epilog=epilog)
    help_text = "pickle file containing a list of statements."
    parser.add_argument("infile", help=help_text)
    args = parser.parse_args()

    infile = args.infile
    filename, file_extension = path.splitext(infile)
    outfile = filename + "_contradictions" + file_extension
    with open(infile, "rb") as f:
        stmts = pickle.load(f)

    preassembler = Preassembler(stmts=stmts, hierarchies=hierarchies)
    contra = preassembler.find_contradicts()

    with open(outfile, 'wb') as f:
        pickle.dump(contra, f)
