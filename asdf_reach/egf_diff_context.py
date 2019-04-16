"""
The idea behind this script is to obtain sentences for an apparent
contradiction, namely that EGF is sometimes described as causing
differentiation, and other times as inhibiting differentiation. These
statements would then be analyzed with the University of Arizona biological
context classifier to determine if the apparent contradiction is reflected in
consistent differences in the context in papers describing these findings.
"""
import json
from collections import Counter
from indra.util import batch_iter
from indra.databases import mesh_client
from indra.statements import stmts_to_json
from indra.sources import indra_db_rest as idr
from indra.literature.pubmed_client import get_metadata_for_ids


pmids = {}

def get_stmts_pmids_mesh(subject, stmt_type, object_list):
    stmts = []
    for obj in object_list:
        idrp = idr.get_statements(subject=subject, object=obj,
                                   stmt_type=stmt_type, ev_limit=10000)
        stmts += idrp.statements

    # Collect the PMIDs for the stmts
    pmids = [e.pmid for s in stmts for e in s.evidence]

    mesh_terms = []
    for batch in batch_iter(pmids, 200):
        pmid_list = list(batch)
        print("Retrieving metadata for %d articles" % len(pmid_list))
        metadata = get_metadata_for_ids(pmid_list)
        for pmid, pmid_meta in metadata.items():
            mesh_terms += [d['mesh'] for d in pmid_meta['mesh_annotations']]
    return (stmts, pmids, mesh_terms)

def proc_mesh(mesh_list, range=100):
    ctr = Counter(mesh_list)
    sort_ctr = sorted([(k, v) for k, v in ctr.items()], key=lambda x: x[1],
                      reverse=True)
    mesh_names = []
    print("Retrieving MESH names")
    for mesh_id, count in sort_ctr[:range]:
        mesh_name = mesh_client.get_mesh_name(mesh_id)
        mesh_names.append((mesh_name, mesh_id, count))
    return mesh_names

diff = ['GO:0030154@GO']
prolif = ['D049109@MESH', 'cell proliferation@TEXT']
#stmt_types = ('Activation', 'Inhibition')

_, _, t1_mesh = get_stmts_pmids_mesh('HMDB06219@HMDB', 'Activation',
                                     diff)
_, _, t2_mesh = get_stmts_pmids_mesh('TGFB@FPLX', 'Activation', diff)


# Convert to JSON and save
# stmts_json = stmts_to_json(stmts)
# with open('egf_%s_diff_stmts.json' % stmt_type.lower(), 'wt') as f:
#    json.dump(stmts_json, f, indent=2)

t1 = proc_mesh(t1_mesh)
t2 = proc_mesh(t2_mesh)
