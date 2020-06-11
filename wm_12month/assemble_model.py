# This script has to be run using INDRA 1.17
import os
import glob
import json
import tqdm
import numpy
import pickle
import logging
from collections import Counter
import indra
import indra.tools.assemble_corpus as ac
from indra.sources import eidos, hume, cwms, sofia
from indra.belief.wm_scorer import get_eidos_scorer
from indra.statements import stmts_to_json, Influence
from indra.preassembler.hierarchy_manager import get_wm_hierarchies
from indra.preassembler.ontology_mapper import OntologyMapper, _load_wm_map


def process_eidos():
    print('Processing Eidos output')
    fnames = sorted(glob.glob('/Users/ben/data/wm/2-Jsonld500/*.jsonld'))
    stmts = []
    for fname in fnames:
        print(fname)
        ep = eidos.process_json_file(fname)
        for stmt in ep.statements:
            for ev in stmt.evidence:
                doc_id = os.path.splitext(os.path.basename(fname))[0]
                ev.annotations['provenance'][0]['document']['@id'] = doc_id
            stmts.append(stmt)
    return stmts


def process_eidos_un():
    print('Processing Eidos output for UN corpus')
    fnames = sorted(glob.glob('/Users/ben/data/wm/2-Jsonld16k/*.jsonld'))
    stmts = []
    for fname in tqdm.tqdm(fnames):
        ep = eidos.process_json_file(fname)
        for stmt in ep.statements:
            for ev in stmt.evidence:
                doc_id = os.path.splitext(os.path.basename(fname))[0]
                ev.annotations['provenance'][0]['document']['@id'] = doc_id
            stmts.append(stmt)
    return stmts


def process_hume():
    print('Processing Hume output')
    #path = 'docs/hume/wm_m12.v8.full.v4.json-ld'
    path = 'docs/hume/wm_m12.v11.500doc.after.json-ld'
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
    ekbs = sorted(glob.glob(path))
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

def dump_mks(stmts):
    ss = sorted(stmts, key=lambda x: len(x.evidence), reverse=True)
    mks = [s.matches_key() for s in ss]
    with open('mks.txt', 'w') as fh:
        for stmt, mk in zip(ss, mks):
            fh.write('%s\t%s\n' % (len(stmt.evidence), mk))

def assemble_stmts(stmts):
    print('Running preassembly')
    hm = get_wm_hierarchies()
    scorer = get_eidos_scorer()
    stmts = ac.run_preassembly(stmts, belief_scorer=scorer,
                               return_toplevel=True,
                               flatten_evidence=True,
                               flatten_evidence_collect_from='supported_by',
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


def surface_details(stmts):
    stmts = ac.merge_groundings(stmts)
    stmts = ac.merge_deltas(stmts)
    return stmts


def set_corpus(stmts, corpus):
    for stmt in stmts:
        for ev in stmt.evidence:
            ev.annotations['provenance'][0]['document']['corpus'] = corpus


def print_source_stats(stmts):
    # Print the number of Statements with a given combination of sources
    source_sets = []
    for stmt in stmts:
        source_sets.append(str({ev.source_api for ev in stmt.evidence}))
    print(Counter(source_sets))

    # Print the number of evidences in total from each source
    sources = []
    for stmt in stmts:
        for ev in stmt.evidence:
            sources.append(ev.source_api)
    print(Counter(sources))


def remove_indicators(stmts):
    remove_keys = ['WHO', 'WDI', 'FAO']
    for stmt in stmts:
        for agent in stmt.agent_list():
            if agent is not None:
                for key in remove_keys:
                    try:
                        agent.db_refs.pop(key)
                    except Exception:
                        pass


if __name__ == '__main__':
    indra.logger.setLevel(logging.DEBUG)
    # With Hume->UN mapping
    eidos_stmts = process_eidos()
    eidos2_stmts = []  # process_eidos_un()
    hume_stmts = process_hume()
    cwms_stmts = process_cwms()
    sofia_stmts = process_sofia()
    stmts = hume_stmts + eidos_stmts + cwms_stmts + sofia_stmts
    set_corpus(stmts, '500m')
    set_corpus(eidos2_stmts, '16k')
    stmts += eidos2_stmts
    #with open('raw_stmts.pkl', 'wb') as fh:
    #    pickle.dump(stmts, fh)
    #with open('raw_stmts.pkl', 'rb') as fh:
    #    stmts = pickle.load(fh)
    # Print raw stmt statistics
    print_source_stats(stmts)

    #stmts = load_pkl('raw_stmts')
    stmts = ontomap_stmts(stmts)
    stmts = assemble_stmts(stmts)
    #with open('assembled_stmts.pkl', 'wb') as fh:
    #    pickle.dump(stmts, fh)
    stmts = surface_details(stmts)
    # Print assembled stmt statistics
    print_source_stats(stmts)
    stmts = standardize_names_groundings(stmts)
    remove_indicators(stmts)
    prefix = 'wm_12_month_4_reader_500m_20190507'
    dump_stmts_json(stmts, '%s.json' % prefix)
    with open('%s.pkl' % prefix, 'wb') as fh:
        pickle.dump(stmts, fh)
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
