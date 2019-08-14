import pickle
from indra.sources import trips
from indra.explanation.model_checker import PysbModelChecker
from util import pklload

pysb_model = pklload('pysb_model')
pysb_stmts = pklload('pysb_stmts')

#stmts_to_check = trips.process_text('BRAF phosphorylates MAPK1.').statements
stmts_to_check = trips.process_text('HRAS phosphorylates MAPK1.').statements

mc = PysbModelChecker(pysb_model, stmts_to_check)
#paths = mc.check_model(max_paths=100, max_path_length=6)
