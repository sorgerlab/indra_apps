import os
import glob
import json
import pickle

from indra.sources import eidos
from indra.statements import stmts_to_json
from indra.belief.wm_scorer import get_eidos_scorer
import indra.tools.assemble_corpus as ac


def assemble_one_corpus():
    """For assembling one of the four corpora."""
    path = '/home/bmg16/data/wm/2-Jsonld'
    corpus_size = '16k'
    prefix = '%s%s' % (path, corpus_size)
    fnames = glob.glob('%s/*.jsonld' % prefix)

    # For large corpus
    all_statements = []
    for idx, fname in enumerate(fnames):
        ep = eidos.process_json_file(fname)
        for stmt in ep.statements:
            for ev in stmt.evidence:
                ev.annotations['provenance'][0]['document']['@id'] = \
                    os.path.basename(fname)

        all_statements += ep.statements
        print('%d: %d' % (idx, len(all_statements)))
    with open('%s/3-Indra%s.pkl' % (prefix, corpus_size), 'wb') as fh:
        pickle.dump(all_statements, fh)

    scorer = get_eidos_scorer()
    assembled_stmts = ac.run_preassembly(all_statements, belief_scorer=scorer,
                                         return_toplevel=False)

    jd = stmts_to_json(assembled_stmts, use_sbo=False)
    with open('%s/3-Indra%s.json' % (prefix, corpus_size), 'w') as fh:
        json.dump(jd, fh, indent=1)


#def assemble_all():
if __name__ == '__main__':
    corpora = {
               #'50': '/home/bmg16/Dropbox/postdoc/darpa/src/indra_apps/' + \
               #      'wm_fao/20181101/2-Jsonld50',
               '500': '/home/bmg16/Dropbox/postdoc/darpa/src/indra_apps/' + \
                      'wm_fao/20181101/2-Jsonld500',
                '16k': '/home/bmg16/data/wm/2-Jsonld16k',
                }
    all_statements = []
    for corpus_size, path in corpora.items():
        fnames = glob.glob('%s/*.jsonld' % path)
        for idx, fname in enumerate(fnames):
            ep = eidos.process_json_file(fname)
            for stmt in ep.statements:
                for ev in stmt.evidence:
                    ev.annotations['provenance'][0]['document']['@id'] = \
                        os.path.basename(fname)
                    ev.annotations['provenance'][0]['document']['corpus'] = \
                        corpus_size
            all_statements += ep.statements
            print('%d: %d' % (idx, len(all_statements)))

    scorer = get_eidos_scorer()
    assembled_stmts = ac.run_preassembly(all_statements, belief_scorer=scorer,
                                         return_toplevel=False)

    jd = stmts_to_json(assembled_stmts, use_sbo=False)
    with open('3-Indra-merged-500-16k.json', 'w') as fh:
        json.dump(jd, fh, indent=1)

#    assemble_all()
