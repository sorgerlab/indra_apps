import os
import glob
import json
import pickle

from indra.sources import eidos
from indra.statements import stmts_to_json
from indra.belief.wm_scorer import get_eidos_scorer
import indra.tools.assemble_corpus as ac


if __name__ == '__main__':
    # For small corpus
    corpus_size = 'Small'
    fnames = glob.glob('SmallJsonld/*.jsonld')

    # For large corpus
    # corpus_size = 'Large'
    # fnames = glob.glob('data/wm/LargeJsonld/*.jsonld')

    version = 3

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
    with open('%sJsonld-INDRA-v%d.pkl' % (corpus_size, version), 'wb') as fh:
        pickle.dump(all_statements, fh)

    scorer = get_eidos_scorer()
    assembled_stmts = ac.run_preassembly(all_statements, belief_scorer=scorer,
                                         return_toplevel=False)

    jd = stmts_to_json(assembled_stmts, use_sbo=False)
    with open('%sJsonld-INDRA-v%d.json' % (corpus_size, version), 'w') as fh:
        json.dump(jd, fh, indent=1)
