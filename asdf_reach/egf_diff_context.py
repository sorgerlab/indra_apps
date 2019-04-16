"""
The idea behind this script is to obtain sentences for an apparent contradiction,
namely that EGF is sometimes described as causing differentiation, and other
times as inhibiting differentiation. These statements would then be analyzed
with the University of Arizona biological context classifier to determine if
the apparent contradiction is reflected in consistent differences in the
context in papers describing these findings.
"""
import json
from indra.sources import indra_db_rest as idr
from indra.statements import stmts_to_json

differentiation = 'GO:0030154@GO'

pmids = []

for stmt_type in ('Activation', 'Inhibition'):
    stmts = idr.get_statements(subject='EGF', object=differentiation,
                               stmt_type=stmt_type, ev_limit=10000)

    stmts_json = stmts_to_json(stmts)
    pmids += [e.pmid for s in stmts_json for e in s.evidence]
    for stmt in stmts_json:
        for 
    with open('egf_%s_diff_stmts.json' % stmt_type.lower(), 'wt') as f:
        json.dump(stmts_json, f, indent=2)




