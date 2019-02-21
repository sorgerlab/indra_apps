from indra.statements import stmts_to_json_file
import indra.tools.assemble_corpus as ac
from assemble_model import process_eidos, assemble_stmts


if __name__ == '__main__':
    stmts = process_eidos()
    stmts_to_json_file(stmts, 'eidos_500m_raw.json')
    stmts = assemble_stmts(stmts)
    stmts = ac.merge_groundings(stmts)
    stmts = ac.merge_deltas(stmts)
    stmts = ac.standardize_names_groundings(stmts)
    stmts_to_json_file(stmts, 'eidos_500m_assembled.json')
