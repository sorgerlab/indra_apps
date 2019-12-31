import indra.tools.assemble_corpus as ac
from indra.assemblers.tsv import TsvAssembler
from indra.statements import stmts_from_json_file


def filter_polarity(stmt):
    if stmt.subj.delta['polarity'] is None or \
            stmt.obj.delta['polarity'] is None:
        return True
    else:
        return False


stmts = stmts_from_json_file('data/.json')
stmts = ac.filter_belief(stmts, 0.8)
stmts = [s for s in stmts if filter_polarity(s)]

ta = TsvAssembler(stmts)
ta.make_model('polarity_curation.csv', add_curation_cols=True)

