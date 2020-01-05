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
    wmg = ag.concept.db_refs['WM'][0]
    wmg = (wmg[0].replace('wm/concept/causal_factor/', ''), wmg[1])
    return wmg


def is_intervention(grounding):
    return True if 'interventions' in grounding else False


def get_text(ev, idx):
    return ev.annotations['agents']['raw_text'][idx]


def get_stmt_ev_pairs(stmts):
    pairs = []
    for stmt in stmts:
        pairs += [(stmt, e) for e in stmt.evidence]
    return pairs


stmts = stmts_from_json_file('data/dart-20200102-grounding-curation-stmts-grounding.json')
stmts = ac.filter_belief(stmts, 0.8)
pairs = get_stmt_ev_pairs(stmts)

stmt_groups = {'': pairs}
nsample = 1000
idx = 1
all_fields = []
for key, pairs in stmt_groups.items():
    sample = [random.choice(pairs) for _ in range(nsample)]
    for stmt, ev in sample:
        fields = {'IDX': idx,
                  'UUID': stmt.uuid,
                  'SUBJ_GROUNDING': get_grounding(stmt.subj)[0],
                  'SUBJ_GROUNDING_SCORE': '%.3f' % get_grounding(stmt.subj)[1],
                  'SUBJ_TEXT': get_text(ev, 0),
                  'SUBJ_INTERVENTION': is_intervention(get_grounding(stmt.subj)[0]),
                  'SUBJ_MENTION_INCORRECT': '',
                  'SUBJ_GROUNDING_CORRECT': '',
                  'OBJ_GROUNDING': get_grounding(stmt.obj)[0],
                  'OBJ_GROUNDING_SCORE': '%.3f' % get_grounding(stmt.obj)[1],
                  'OBJ_TEXT': get_text(ev, 1),
                  'OBJ_INTERVENTION': is_intervention(get_grounding(stmt.obj)[0]),
                  'OBJ_MENTION_INCORRECT': '',
                  'OBJ_GROUNDING_CORRECT': '',
                  'CURATOR': '',
                  'READER': ev.source_api,
                  'TEXT': ev.text}
        all_fields.append(fields)
        idx += 1
rows = [list(all_fields[0].keys())]
for fields in all_fields:
    rows.append(list(fields.values()))
write_unicode_csv('grounding_sample.csv', rows)

