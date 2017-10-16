from matplotlib_venn import venn2, venn3
from matplotlib import pyplot as plt

from indra.statements import *
from indra.util import _require_python3
from indra.util import read_unicode_csv
from indra.databases import hgnc_client
from indra.db.query_db_stmts import *
from indra.tools import assemble_corpus as ac

def _get_ids(hgnc_name):
    hgnc_id = hgnc_client.get_hgnc_id(hgnc_name)
    up_id = hgnc_client.get_uniprot_id(hgnc_id)
    return {'HGNC': hgnc_id, 'UP': up_id}


def _get_rels(stmts):
    return set([(s.subj.name, s.obj.name, s.__class__.__name__) for s in stmts])

def get_pc_expression(filename='PathwayCommons9.All.hgnc.sif'):
    stmts = []
    for row in read_unicode_csv(filename, skiprows=1, delimiter='\t'):
        if row[1] != 'controls-expression-of':
            continue
        subj_name = row[0]
        obj_name = row[2]
        subj = Agent(subj_name, db_refs=_get_ids(subj_name))
        obj = Agent(obj_name, db_refs=_get_ids(obj_name))
        stmt = IncreaseAmount(subj, obj)
        stmts.append(stmt)
    return stmts


def get_indra_expression():
    #inc_stmts = by_gene_role_type(stmt_type='IncreaseAmount')
    #dec_stmts = by_gene_role_type(stmt_type='DecreaseAmount')
    #stmts = inc_stmts + dec_stmts
    #ac.dump_statements(stmts, 'indra_regulate_amount_stmts.pkl')
    #stmts = ac.load_statements('indra_regulate_amount_stmts.pkl')
    #stmts = ac.map_grounding(stmts)
    # Expand families before site mapping
    #stmts = ac.expand_families(stmts)
    #stmts = ac.filter_grounded_only(stmts)
    #stmts = ac.map_sequence(stmts)
    #stmts = ac.run_preassembly(stmts, poolsize=4,
    #                           save='indra_regulate_amount_pre.pkl')
    stmts = ac.load_statements('indra_regulate_amount_pre.pkl')
    stmts = ac.filter_human_only(stmts)
    stmts = ac.filter_genes_only(stmts)
    stmts = [s for s in stmts if s.agent_list()[0] is not None]
    return stmts

if __name__ == '__main__':
    indra_stmts = get_indra_expression()
    pc_stmts = get_pc_expression()

    indra_rels = _get_rels(indra_stmts)
    pc_rels = _get_rels(pc_stmts)

    plt.ion()
    plt.figure()
    venn2((indra_rels, pc_rels),
          set_labels=('REACH/INDRA/SIGNOR', 'Pathway Commons'))
    plt.savefig('indra_expr_overlap.pdf')


