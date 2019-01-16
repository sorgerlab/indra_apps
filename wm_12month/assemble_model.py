import os
import glob
import json
import tqdm
import numpy
import pickle
import indra.tools.assemble_corpus as ac
from indra.sources import eidos, hume, cwms, sofia
from indra.belief.wm_scorer import get_eidos_scorer
from indra.statements import stmts_to_json, Influence
from indra.preassembler.hierarchy_manager import get_wm_hierarchies
from indra.preassembler.ontology_mapper import OntologyMapper, _load_wm_map


def process_eidos():
    print('Processing Eidos output')
    fnames = glob.glob('docs/eidos/*.jsonld')
    stmts = []
    for fname in fnames:
        print(fname)
        ep = eidos.process_json_file(fname)
        for stmt in ep.statements:
            for ev in stmt.evidence:
                ev.annotations['provenance'][0]['document']['@id'] = \
                    os.path.basename(fname)
            stmts.append(stmt)
    return stmts


def process_eidos_un():
    print('Processing Eidos output for UN corpus')
    fnames = glob.glob('/Users/ben/data/wm/2-Jsonld16k/*.jsonld')
    stmts = []
    for fname in tqdm.tqdm(fnames):
        ep = eidos.process_json_file(fname)
        for stmt in ep.statements:
            for ev in stmt.evidence:
                ev.annotations['provenance'][0]['document']['@id'] = \
                    os.path.basename(fname)
            stmts.append(stmt)
    return stmts


def process_hume():
    print('Processing Hume output')
    path = 'docs/hume/wm_m12.v8.full.v4.json-ld'
    hp = hume.process_jsonld_file(path)
    return hp.statements


def process_sofia():
    print('Processing Sofia output')
    fname = 'docs/sofia/MITRE_AnnualEval_v1.xlsx'
    sp = sofia.process_table(fname)
    for stmt in sp.statements:
        for ev in stmt.evidence:
            prov = [{'document': {'@id': ev.pmid}}]
            ev.annotations['provenance'] = prov
    return sp.statements


def process_cwms():
    print('Processing CWMS output')
    path = 'docs/cwms/20181114/*.ekb'
    ekbs = glob.glob(path)
    stmts = []
    for ekb in ekbs:
        cp = cwms.process_ekb_file(ekb)
        stmts += cp.statements
    for stmt in stmts:
        for ev in stmt.evidence:
            prov = [{'document': {'@id': ev.pmid}}]
            ev.annotations['provenance'] = prov
    return stmts


def ontomap_stmts(stmts, hume_auto_mapping=True):
    print('Ontology mapping')
    if hume_auto_mapping:
        wm_ontomap = _load_wm_map()
    else:
        wm_ontomap = _load_wm_map(exclude_auto=[('HUME', 'UN')])
    om = OntologyMapper(stmts, wm_ontomap, scored=True, symmetric=False)
    om.map_statements()
    return stmts


def assemble_stmts(stmts):
    print('Running preassembly')
    hm = get_wm_hierarchies()
    scorer = get_eidos_scorer()
    stmts = ac.run_preassembly(stmts, belief_scorer=scorer,
                               return_toplevel=False,
                               poolsize=2)
    return stmts


def dump_stmts_json(stmts, fname):
    print('Dumping statements into JSON')
    jd = stmts_to_json(stmts, use_sbo=False)
    with open(fname, 'w') as fh:
        json.dump(jd, fh, indent=1)


def standardize_names_groundings(stmts):
    """Standardize the names of Concepts with respect to an ontology."""
    print('Standardize names to groundings')
    for stmt in stmts:
        for concept in stmt.agent_list():
            db_ns, db_id = concept.get_grounding()
            if db_id is not None:
                if isinstance(db_id, list):
                    db_id = db_id[0][0].split('/')[-1]
                else:
                    db_id = db_id.split('/')[-1]
                db_id = db_id.replace('|', ' ')
                db_id = db_id.replace('_', ' ')
                db_id = db_id.replace('ONT::', '')
                db_id = db_id.capitalize()
                concept.name = db_id
    return stmts
    """
    for stmt in stmts:
        for idx, agent in enumerate(stmt.agent_list()):
            if 'UN' in agent.db_refs:
                all_un_scores = []
                for ev in stmt.evidence:
                    agent_annots = ev.annotations.get('agents')
                    if agent_annots and 'raw_grounding' in agent_annots and \
                        'UN' in  agent_annots['raw_grounding'][idx]:
                        un_score = agent_annots['raw_grounding'][idx]['UN'][0][1]
                        all_un_scores.append(un_score)
                if all_un_scores:
                    noisy_or_score = 1 - numpy.prod([1-x for x in
                                                     all_un_scores])
                    print('%s -> %.2f' % (str(all_un_scores), noisy_or_score))
                    agent.db_refs['UN'][0] = (agent.db_refs['UN'][0][0],
                                              noisy_or_score)
   """


def preferential_un_grounding(stmts):
    print('Bubble up UN groundings')
    for stmt in stmts:
        if not isinstance(stmt, Influence):
            continue
        for idx, agent in enumerate(stmt.agent_list()):
            un_groundings = []
            for ev in stmt.evidence:
                raw_grounding = ev.annotations['agents']['raw_grounding'][idx]
                raw_text = ev.annotations['agents']['raw_grounding'][idx]['TEXT']
                if 'UN' in raw_grounding:
                    un_groundings.append((raw_grounding['UN'][0], raw_text))
            if un_groundings:
                for fr, txt in un_groundings:
                    print('%s: %s' % (txt, str(fr)))
                print('=====')


def filter_to_hume_interventions(stmts):
    """Filter out UN intervention nodes except the ones in the include list."""
    include = ['provision_of_free_food_distribution',
               'provision_of_cash_transfer']
    filter_out = [False] * len(stmts)
    print('Filtering %d stmts' % len(stmts))
    for idx, stmt in enumerate(stmts):
        for agent in stmt.agent_list():
            if 'UN' in agent.db_refs:
                ug = agent.db_refs['UN'][0][0]
                if ug.startswith('UN/interventions'):
                    if not ug.endswith(include[0]) and not \
                        ug.endswith(include[1]):
                        filter_out[idx] = True
    stmts = [s for s, f in zip(stmts, filter_out) if not f]
    print('Filtered to %d stmts' % len(stmts))
    return stmts


def load_pkl(prefix):
    fname = '%s.pkl' % prefix
    print('Loading %s' % fname)
    with open(fname, 'rb') as fh:
        obj = pickle.load(fh)
    return obj


def get_stats(stmts):
    grounding_to_text = {}
    for stmt in stmts:
        for agent in stmt.agent_list():
            if 'UN' in agent.db_refs:
                gr = agent.db_refs['UN'][0][0]
                txt = agent.db_refs['TEXT']
                try:
                    grounding_to_text[gr].append(txt)
                except KeyError:
                    grounding_to_text[gr] = [txt]
    return grounding_to_text


if __name__ == '__main__':
    # With Hume->UN mapping
    hume_stmts = process_hume()
    eidos_stmts = process_eidos()
    eidos2_stmts = [] # process_eidos_un()
    cwms_stmts = process_cwms()
    sofia_stmts = process_sofia()
    stmts = hume_stmts + eidos_stmts + eidos2_stmts + cwms_stmts + sofia_stmts
    #stmts = load_pkl('raw_stmts')
    stmts = ontomap_stmts(stmts)
    stmts = assemble_stmts(stmts)
    #stmts = standardize_names_groundings(stmts)
    dump_stmts_json(stmts, 'wm_12_month_4_reader_20190115.json')
    """
    # Without Hume->UN mapping
    # Without intervention other than food or cash
    hume_stmts = process_hume()
    eidos_stmts = process_eidos()
    cwms_stmts = process_cwms()
    sofia_stmts = process_sofia()
    stmts = hume_stmts + eidos_stmts + cwms_stmts + sofia_stmts
    stmts = ontomap_stmts(stmts, False)
    stmts = filter_to_hume_interventions(stmts)
    stmts = assemble_stmts(stmts)
    stmts = standardize_names_groundings(stmts)
    dump_stmts_json(stmts, 'wm_12_month_4_reader_20181129_noautomap_filtered.json')
    # Without Hume->UN mapping
    hume_stmts = process_hume()
    eidos_stmts = process_eidos()
    cwms_stmts = process_cwms()
    sofia_stmts = process_sofia()
    stmts = hume_stmts + eidos_stmts + cwms_stmts + sofia_stmts
    stmts = ontomap_stmts(stmts, False)
    stmts = assemble_stmts(stmts)
    stmts = standardize_names_groundings(stmts)
    dump_stmts_json(stmts, 'wm_12_month_4_reader_20181129_noautomap_unfiltered.json')
    #preferential_un_grounding(stmts)
    """
