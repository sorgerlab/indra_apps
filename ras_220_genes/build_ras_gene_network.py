import os
import csv
import pickle
import indra
from indra.tools.gene_network import GeneNetwork
from indra.tools import assemble_corpus as ac

# STEP 0: Get gene list
gene_list = []
# Get gene list from ras_pathway_proteins.csv
fname = os.path.join(indra.__path__[0], 'resources',
                     'ras_pathway_proteins.csv')
with open(fname, 'r') as f:
    csvreader = csv.reader(f, delimiter='\t')
    for row in csvreader:
        gene_list.append(row[0].strip())

gn = GeneNetwork(gene_list, 'ras_genes')
stmts = gn.get_statements(filter=True)
grounded_stmts = ac.filter_grounded_only(stmts)
results = ac.run_preassembly(grounded_stmts)
with open('ras_220_gn_stmts.pkl', 'wb') as f:
    pickle.dump(results, f)

