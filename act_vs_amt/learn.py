from collections import defaultdict
from indra.sources import signor
from indra.statements import RegulateActivity, RegulateAmount
from indra.tools import assemble_corpus as ac
from indra.sources import indra_db_rest
from indra_db.client.principal.curation import get_curations
from indra_db.client import get_statements_from_hashes
from adeft.modeling.classify import AdeftClassifier


def get_signor_stmts():
    """Return a list of activity and a list of amount regulation stmts."""
    sp = signor.process_from_web()
    return ac.filter_by_type(sp.statements, RegulateActivity), \
        ac.filter_by_type(sp.statements, RegulateAmount)


def get_signor_xor_texts(act_stmts, amt_stmts):
    """Return evidence text for activity/amount only (exclusive) regulations."""

    # We build up a set of A-B keys to find exclusively activity vs amount
    # regulation statements
    act_dict = defaultdict(list)
    for stmt in act_stmts:
        key = (stmt.subj.get_grounding(),
               stmt.obj.get_grounding())
        act_dict[key].append(stmt)
    amt_dict = defaultdict(list)
    for stmt in amt_stmts:
        key = (stmt.subj.get_grounding(),
               stmt.obj.get_grounding())
        amt_dict[key].append(stmt)
    disallowed_keys = set(act_dict.keys()) & set(amt_dict.keys())
    print('%s keys are overlapping' % len(disallowed_keys))
    act_dict = {k: v for k, v in act_dict.items() if k not in disallowed_keys}
    amt_dict = {k: v for k, v in amt_dict.items() if k not in disallowed_keys}

    act_txts = []
    for stmts in act_dict.values():
        act_txts += get_ev_texts(stmts)
    amt_txts = []
    for stmts in amt_dict.values():
        amt_txts += get_ev_texts(stmts)
    # We make the lists unique because there's quite a bit
    # of duplication
    return list(set(act_txts)), list(set(amt_txts))


def get_curation_texts():
    """Return activity/amount evidence texts based on curations."""
    # FIXME: get_statements_from_hashes will get the right statements but we
    # collect _all_ evidences of these statements, not just the ones that
    # were specifically curated. It might make more sense to filter down
    # the set of evidence to the specific evidence hashes to which each
    # curation corresponds.

    curations = get_curations(tag='act_vs_amt')
    stmts = get_statements_from_hashes([cur.pa_hash for cur in curations])
    # Note that these are flipped because the curation implies opposite
    amt_txts = get_ev_texts(ac.filter_by_type(stmts, RegulateActivity))
    act_txts = get_ev_texts(ac.filter_by_type(stmts, RegulateAmount))

    curations = get_curations(tag='correct')
    stmts = get_statements_from_hashes([cur.pa_hash for cur in curations])
    amt_txts += get_ev_texts(ac.filter_by_type(stmts, RegulateAmount))
    act_txts += get_ev_texts(ac.filter_by_type(stmts, RegulateActivity))

    return act_txts, amt_txts


def get_ev_texts(stmts):
    """Return evidence texts for a given list of statements"""
    txts = []
    for stmt in stmts:
        for ev in stmt.evidence:
            if ev.text:
                txts.append(ev.text)
    return txts


if __name__ == '__main__':
    # Approach 1: get training examples from curations
    # act_txts, amt_txts = get_curation_texts()

    # Approach 2: get training examples from Signor sentences
    signor_act, signor_amt = get_signor_stmts()
    act_txts, amt_txts = get_signor_xor_texts(signor_act, signor_amt)

    # Approach 3: use Signor to find A->B pairs that are exclusively
    # activity or amount regulations, and then find corresponding evidence
    # sentences from reading for A->B Statements.
    # TODO

    # Prepare training examples and labels
    texts = act_txts + amt_txts
    labels = ['act']*len(act_txts) + ['amt']*len(amt_txts)
    # Create classifier
    cl = AdeftClassifier(texts, labels)
    param_grid = {'C': [10.0], 'max_features': [100, 1000],
                  'ngram_range': [(1, 2)]}
    # Do cross-validation
    cl.cv(texts, labels, param_grid, cv=5)
    print(cl.stats)
    cl_model_info = cl.get_model_info()
