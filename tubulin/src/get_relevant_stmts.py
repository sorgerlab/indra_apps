import csv
from collections import defaultdict
from indra.db import client
from indra.statements import *
from indra.tools import assemble_corpus as ac

def get_phosphorylation_statements(residue_file):
    sites = defaultdict(list)
    with open('../work/genes_with_residues.csv', 'rt') as f:
        csvreader = csv.reader(f, delimiter=',')
        for gene, site in csvreader:
            sites[gene].append(site)

    stmts = []
    counter = 0
    for gene, res_list in sites.items():
        print("%d of %d: getting Phosphorylation statements for %s" %
              (counter, len(sites), gene))
        phos_stmts = client.get_statements_by_gene_role_type(
                agent_id=gene, role='OBJECT', stmt_type='Phosphorylation')
        for ps in phos_stmts:
            if ps.enz is not None and ps.position in res_list:
                stmts.append(ps)
        counter += 1
    return stmts

def get_stmt_subject_object(stmts, type):
    if type not in ['SUBJECT', 'OBJECT']:
        raise ValueError('type must be one of (SUBJECT, OBJECT)')
    stmts = ac.filter_by_type(stmts, Complex, invert=True)
    stmts = ac.filter_by_type(stmts, SelfModification, invert=True)
    stmt_agents = []
    for stmt in stmts:
        assert len(stmt.agent_list()) == 2
        if type == 'SUBJECT':
            ag = stmt.agent_list()[0]
        else:
            ag = stmt.agent_list()[1]
        # Get HGNC and FPLX groundings, preferring HGNC to FPLX IDs
        # Other types of nodes (chemicals, biological processes, etc.) are
        # currently ignored
        # TODO: Include ungrounded agents (with only 'TEXT' in db_refs)
        if 'HGNC' in ag.db_refs:
            stmt_agents.append(('HGNC': db_refs['HGNC']))
        elif 'FPLX' in ag.db_refs:
            stmt_agents.append(('FPLX': db_refs['FPLX']))
    return stmt_agents

"""
def get_reachable_nodes(source_list, target_list, max_depth):
    if max_depth < 1:
        raise ValueError("max_depth must be at least 1")
    # Look at successors first
    f_level = {0: set([source_list])}
    b_level = {0: set([target_list])}
    for i in range(1, max_depth+1):
        reachable_set = set()
        for node in f_level[i-1]:
            successor_stmts = client.get_statements_by_gene_role_type(
                                agent_id='
"""
