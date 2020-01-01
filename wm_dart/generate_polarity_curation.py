import random
import indra.tools.assemble_corpus as ac
from indra.util import write_unicode_csv
from indra.assemblers.tsv import TsvAssembler
from indra.statements import stmts_from_json_file


def filter_subj_undef(pair):
    stmt, ev = pair
    if ev.annotations['subj_polarity'] is None and \
            ev.annotations['obj_polarity'] is not None:
        return True
    return False


def filter_obj_undef(pair):
    stmt, ev = pair
    if ev.annotations['subj_polarity'] is not None and \
            ev.annotations['obj_polarity'] is None:
        return True
    return False


def filter_both_undef(pair):
    stmt, ev = pair
    if ev.annotations['subj_polarity'] is None and \
            ev.annotations['obj_polarity'] is None:
        return True
    return False


def get_grounding(ag):
    wmg = ag.concept.db_refs['WM'][0][0]
    wmg = wmg.replace('wm/concept/causal_factor/', '')
    return wmg


def get_text(ev, idx):
    return ev.annotations['agents']['raw_text'][idx]


def get_eidos_stmt_ev_pairs(stmts):
    pairs = []
    for stmt in stmts:
        pairs += [(stmt, e) for e in stmt.evidence if e.source_api == 'eidos']
    return pairs


stmts = stmts_from_json_file('data/dart-20191223-stmts-grounding.json')
stmts = ac.filter_belief(stmts, 0.8)
pairs = get_eidos_stmt_ev_pairs(stmts)
subj_undef = [s for s in pairs if filter_subj_undef(s)]
obj_undef = [s for s in pairs if filter_obj_undef(s)]
both_undef = [s for s in pairs if filter_both_undef(s)]

stmt_groups = {'SUBJ': subj_undef, 'OBJ': obj_undef, 'BOTH': both_undef}
nsample = 500
idx = 1
all_fields = []
for key, pairs in stmt_groups.items():
    sample = [random.choice(pairs) for _ in range(nsample)]
    for stmt, ev in sample:
        fields = {'IDX': idx,
                  'POLARITY_MISSING': key,
                  'UUID': stmt.uuid,
                  'SUBJ_GROUNDING': get_grounding(stmt.subj),
                  'OBJ_GROUNDING': get_grounding(stmt.obj),
                  'SUBJ_TEXT': get_text(ev, 0),
                  'OBJ_TEXT': get_text(ev, 1),
                  'SUBJ_POLARITY': ev.annotations['subj_polarity'],
                  'OBJ_POLARITY': ev.annotations['obj_polarity'],
                  'CURATOR': '',
                  'INCORRECT': '',
                  'POLARITY_POSITIVE': '',
                  'TEXT': ev.text}
        all_fields.append(fields)
        idx += 1
rows = [list(all_fields[0].keys())]
for fields in all_fields:
    rows.append(list(fields.values()))
write_unicode_csv('polarity_sample.csv', rows)

