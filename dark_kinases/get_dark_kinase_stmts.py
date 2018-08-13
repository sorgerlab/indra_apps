"""Reads a list of kinases annotated with which ones are considered "dark"
kinases, and retrieves a list of statements associated with them from the INDRA
database."""

import pickle
import pandas as pd
from indra.db import client as dbc
from indra.databases import hgnc_client

dk_col = 'in_IDG_darkkinases'
kinase_file = 'Table_001_all_kinases.csv'

if __name__ == '__main__':
    kinases = pd.read_csv(kinase_file, delimiter=',', header=0)
    dark_kinases = kinases[kinases[dk_col]]

    results = {}
    for egid in dark_kinases.gene_id:
        hgnc_id = hgnc_client.get_hgnc_from_entrez(str(egid))
        if hgnc_id is None:
            print("No HGNC id for Entrez Gene id %s" % egid)
            continue
        gene_sym = hgnc_client.get_hgnc_name(hgnc_id)
        if gene_sym is None:
            print("No symbol for gene id %s" % hgnc_id)
        stmts = dbc.get_statements_by_gene_role_type(agent_id=hgnc_id,
                                                     agent_ns='HGNC')
        results[gene_sym] = stmts
    with open('dark_kinase_stmts.pkl', 'wb') as f:
        pickle.dump(results, f)
