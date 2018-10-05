import glob
import json

from indra.sources import eidos
from indra.statements import stmts_to_json
import indra.tools.assemble_corpus as ac


if __name__ == '__main__':
    fnames = glob.glob('SmallJsonld/*.jsonld')
    all_statements = []
    for fname in fnames:
        ep = eidos.process_json_file(fname)
        all_statements += ep.statements

    assembled_stmts = ac.run_preassembly(all_statements)

    jd = stmts_to_json(assembled_stmts)
    with open('SmallJsonld-INDRA.json', 'w') as fh:
        json.dump(jd, fh, indent=1)
