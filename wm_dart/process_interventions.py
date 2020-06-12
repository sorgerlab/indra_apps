import os
import glob
import copy
import tqdm
import json
import yaml
import pickle
import logging
import requests
from collections import defaultdict
from datetime import datetime
from indra.sources import eidos, hume, sofia, cwms
from indra.tools.live_curation import Corpus
from indra.tools import assemble_corpus as ac
from indra.belief.wm_scorer import get_eidos_scorer
from indra.preassembler.custom_preassembly import *
from indra.statements import Event, Influence, Association
from indra.ontology.world import load_world_ontology

import indra
indra.logger.setLevel(logging.DEBUG)

logger = logging.getLogger()
#data_path = os.path.join(os.path.expanduser('~'), 'data', 'wm', 'dart')
#data_path = os.path.join('.', 'data')
data_path = os.path.join(os.path.sep, 'dart', 'data')


wm_ont_url = ('https://raw.githubusercontent.com/WorldModelers/'
              'Ontologies/master/wm_with_flattened_interventions_metadata.yml')


def load_eidos(limit=None, cached=True):
    logger.info('Loading Eidos statements')
    pkl_name = os.path.join(data_path, 'eidos', 'stmts_intervention.pkl')
    if cached:
        if os.path.exists(pkl_name):
            with open(pkl_name, 'rb') as fh:
                stmts = pickle.load(fh)
                logger.info(f'Loaded {len(stmts)} statements')
                return stmts
    fnames = glob.glob(os.path.join(data_path, 'eidos/jsonldDir/*.jsonld'))

    stmts = []
    for fname in tqdm.tqdm(fnames[:limit]):
        doc_id = os.path.basename(fname).split('.')[0]
        ep = eidos.process_json_file(fname)
        fix_provenance(ep.statements, doc_id)
        stmts += ep.statements
    logger.info(f'Loaded {len(stmts)} statements from Eidos')
    with open(pkl_name, 'wb') as fh:
        pickle.dump(stmts, fh)
    return stmts


def load_hume(cached=True):
    logger.info('Loading Hume statements')
    pkl_name = os.path.join(data_path, 'hume', 'stmts_intervention.pkl')
    if cached:
        if os.path.exists(pkl_name):
            with open(pkl_name, 'rb') as fh:
                stmts = pickle.load(fh)
                logger.info(f'Loaded {len(stmts)} statements')
                return stmts
    fnames = glob.glob(os.path.join(data_path, 'hume',
                                    'wm_thanksgiving_intervention.030920', '*.json-ld'))
    stmts = []
    for fname in tqdm.tqdm(fnames):
        hp = hume.process_jsonld_file(fname)
        stmts += hp.statements
    logger.info(f'Loaded {len(stmts)} statements from Hume')
    with open(pkl_name, 'wb') as fh:
        pickle.dump(stmts, fh)
    return stmts


def load_cwms(cached=True):
    logger.info('Loading CWMS statements')
    pkl_name = os.path.join(data_path, 'cwms', 'stmts_regrounded.pkl')
    if cached:
        if os.path.exists(pkl_name):
            with open(pkl_name, 'rb') as fh:
                stmts = pickle.load(fh)
                logger.info(f'Loaded {len(stmts)} statements')
                return stmts
    fnames = glob.glob(os.path.join(data_path, 'cwms', 'ekbs', '*.ekb'))
    #fnames += glob.glob(os.path.join(data_path, 'cwms', 'j_ekbs', '*.ekb'))
    stmts = []
    for fname in tqdm.tqdm(fnames):
        logger.info(f'Processing {fname}')
        try:
            cp = cwms.process_ekb_file(fname)
        except Exception as e:
            continue
        stmts += cp.statements
    for stmt in stmts:
        for ev in stmt.evidence:
            ev.annotations['provenance'] = [{'@type': 'Provenance',
                                             'document': {
                                                 '@id': ev.pmid}}]
    logger.info(f'Loaded {len(stmts)} statements from CWMS')
    with open(pkl_name, 'wb') as fh:
        pickle.dump(stmts, fh)
    return stmts


def load_sofia(cached=True):
    logger.info('Loading Sofia statements')
    pkl_name = os.path.join(data_path, 'sofia', 'stmts_regrounded.pkl')
    if cached:
        if os.path.exists(pkl_name):
            with open(pkl_name, 'rb') as fh:
                stmts = pickle.load(fh)
                logger.info(f'Loaded {len(stmts)} statements')
                return stmts
    fnames = glob.glob(os.path.join(data_path,
                                    'sofia/*.xlsx'))

    stmts = []
    doc_ids = set()
    for idx, fname in enumerate(fnames):
        logger.info(f'Processing {fname}')
        sp = sofia.process_table(fname)
        if idx == 0:
            for stmt in sp.statements:
                for ev in stmt.evidence:
                    doc_id = ev.pmid.split('.')[0]
                    doc_ids.add(doc_id)
            stmts += sp.statements
        else:
            for stmt in sp.statements:
                doc_id = stmt.evidence[0].pmid.split('.')[0]
                if doc_id not in doc_ids:
                    stmts.append(stmt)
    for stmt in stmts:
        for ev in stmt.evidence:
            doc_id = ev.pmid.split('.')[0]
            ev.annotations['provenance'] = [{'@type': 'Provenance',
                                             'document': {
                                                 '@id': doc_id}}]
    logger.info(f'Loaded {len(stmts)} statements from Sofia')
    with open(pkl_name, 'wb') as fh:
        pickle.dump(stmts, fh)
    return stmts


def fix_provenance(stmts, doc_id):
    """Move the document identifiers in evidences."""
    for stmt in stmts:
        for ev in stmt.evidence:
            prov = ev.annotations['provenance'][0]['document']
            prov['@id'] = doc_id


def remove_namespaces(stmts, namespaces):
    """Remove unnecessary namespaces from Concept grounding."""
    logger.info('Removing unnecessary namespaces')
    for stmt in stmts:
        for agent in stmt.agent_list():
            for namespace in namespaces:
                if namespace in copy.deepcopy(agent.db_refs):
                    agent.db_refs.pop(namespace, None)
    logger.info('Finished removing unnecessary namespaces')


def remove_raw_grounding(stmts):
    """Remove the raw_grounding annotation to decrease output size."""
    for stmt in stmts:
        for ev in stmt.evidence:
            if not ev.annotations:
                continue
            agents = ev.annotations.get('agents')
            if not agents:
                continue
            if 'raw_grounding' in agents:
                agents.pop('raw_grounding', None)


def get_events(stmts):
    """Return a list of all standalone events from a list of statements."""
    events = []
    for stmt in stmts:
        stmt = copy.deepcopy(stmt)
        if isinstance(stmt, Influence):
            for member in [stmt.subj, stmt.obj]:
                member.evidence = stmt.evidence[:]
                # Remove the context since it may be for the other member
                for ev in member.evidence:
                    ev.context = None
                events.append(member)
        elif isinstance(stmt, Association):
            for member in stmt.members:
                member.evidence = stmt.evidence[:]
                # Remove the context since it may be for the other member
                for ev in member.evidence:
                    ev.context = None
                events.append(member)
        elif isinstance(stmt, Event):
            events.append(stmt)
    return events


def get_non_events(stmts):
    """Return a list of statements that aren't Events"""
    return [st for st in stmts if not isinstance(st, Event)]


def check_event_context(events):
    for event in events:
        if not event.context and event.evidence[0].context:
            assert False, ('Event context issue', event, event.evidence)
        ej = event.to_json()
        if 'context' not in ej and 'context' in ej['evidence'][0]:
            assert False, ('Event context issue', event, event.evidence)


def reground_stmts(stmts, ont_manager, namespace, eidos_reader=None,
                   overwrite=True, port=6666):
    logger.info(f'Regrounding {len(stmts)} statements')
    # Send the latest ontology and list of concept texts to Eidos
    yaml_str = yaml.dump(ont_manager.yaml_root)
    concepts = []
    for stmt in stmts:
        for concept in stmt.agent_list():
            #concept_txt = concept.db_refs.get('TEXT')
            concept_txt = concept.name
            concepts.append(concept_txt)
    # Either use an EidosReader instance or a local web service
    if eidos_reader:
        groundings = eidos_reader.reground_texts(concepts, yaml_str)
    else:
        res = requests.post(f'http://localhost:{port}/reground_text',
                            json={'text': concepts, 'ont_yml': yaml_str})
        groundings = res.json()
    # Update the corpus with new groundings
    idx = 0
    logger.info(f'Setting new grounding for {len(stmts)} statements')
    for stmt in stmts:
        for concept in stmt.agent_list():
            if overwrite:
                if groundings[idx]:
                    concept.db_refs[namespace] = groundings[idx]
                elif namespace in concept.db_refs:
                    concept.db_refs.pop(namespace, None)
            else:
                if (namespace not in concept.db_refs) and groundings[idx]:
                    concept.db_refs[namespace] = groundings[idx]
            idx += 1
    logger.info(f'Finished setting new grounding for {len(stmts)} statements')
    return stmts


def remove_hume_redundant(stmts, matches_fun):
    logger.info(f'Removing Hume redundancies on {len(stmts)} statements.')
    raw_stmt_groups = defaultdict(list)
    for stmt in stmts:
        sh = stmt.get_hash(matches_fun=matches_fun, refresh=True)
        eh = (stmt.evidence[0].pmid, stmt.evidence[0].text,
              stmt.subj.concept.name, stmt.obj.concept.name,
              stmt.evidence[0].annotations['adjectives'])
        key = str((sh, eh))
        raw_stmt_groups[key].append(stmt)
    new_stmts = list({group[0] for group in raw_stmt_groups.values()})
    logger.info(f'{len(new_stmts)} statements after filter.')
    return new_stmts


def fix_wm_ontology(stmts):
    for stmt in stmts:
        for concept in stmt.agent_list():
            if 'WM' in concept.db_refs:
                concept.db_refs['WM'] = [(entry.replace(' ', '_'), score)
                                         for entry, score in
                                         concept.db_refs['WM']]


def print_statistics(stmts):
    ev_tot = sum([len(stmt.evidence) for stmt in stmts])
    logger.info(f'Total evidence {ev_tot} for {len(stmts)} statements.')


def print_grounding_statistics(stmts, limit=None):
    groundings = defaultdict(int)
    for stmt in stmts:
        for ag in stmt.agent_list():
            try:
                wm_highest = ag.db_refs['WM'][0][0]
                groundings[wm_highest] += 1
            except KeyError:
                continue
    logger.info('Grounding concepts and their counts')
    for grounding, count in sorted(groundings.items(), key=lambda x: x[1],
                                   reverse=True)[:limit]:
        logger.info(f'{grounding} : {count}')


def print_document_statistics(stmts):
    doc_ids = set()
    for stmt in stmts:
        doc_id = stmt.evidence[0].annotations['provenance'][0]['document']['@id']
        assert len(doc_id) == 32
        doc_ids.add(doc_id)
    logger.info(
        f'Extracted {len(stmts)} statements from {len(doc_ids)} documents')


def filter_context_date(stmts, from_date=None, to_date=None):
    logger.info(f'Filtering dates on {len(stmts)} statements')
    if not from_date and not to_date:
        return stmts
    new_stmts = []
    for stmt in stmts:
        doc_id = \
            stmt.evidence[0].annotations['provenance'][0]['document']['@id']
        if isinstance(stmt, Influence):
            events = [stmt.subj, stmt.obj]
        elif isinstance(stmt, Association):
            events = stmt.members
        else:
            events = [stmt]
        for event in events:
            if event.context and event.context.time:
                if from_date and event.context.time.start and \
                        (event.context.time.start < from_date):
                    logger.info(f'Removing date {event.context.time.start}'
                                f'({event.context.time.text}) from {doc_id}')
                    event.context.time = None
                if to_date and event.context.time.end and \
                        (event.context.time.end > to_date):
                    event.context.time = None
                    logger.info(f'Removing date {event.context.time.end}'
                                f'({event.context.time.text}) from {doc_id}')
        new_stmts.append(stmt)
    logger.info(f'{len(new_stmts)} statements after date filter')
    return new_stmts


def filter_groundings(stmts):
    with open('groundings_to_exclude.txt', 'r') as f: 
        groundings_to_exclude = [l.strip() for l in f.readlines()]
    stmts = ac.filter_by_db_refs(
        stmts, 'WM', groundings_to_exclude, 'all', invert=True)
    return stmts


def set_positive_polarities(stmts):
    for stmt in stmts:
        if isinstance(stmt, Influence):
            for event in [stmt.subj, stmt.obj]:
                if event.delta.polarity is None:
                    event.delta.polarity = 1
    return stmts


def filter_to_hume_interventions_only(stmts):
    def get_grounding(ag):
        wmg = ag.concept.db_refs['WM'][0]
        wmg = (wmg[0].replace('wm/concept/causal_factor/', ''), wmg[1])
        return wmg

    def is_intervention(grounding):
        return True if 'interventions' in grounding else False

    def remove_top_interventions(db_refs):
        found = None
        for idx, (gr, score) in enumerate(db_refs['WM']):
            if not is_intervention(gr):
                found = idx
                break
        # If no non-intervention was found, we remove all WM groundings
        if found is None:
            logger.info('No groundings remaining, removing WM')
            db_refs.pop('WM', None)
        else:
            if idx > 0:
                logger.info('Removing first %d groundings' % idx)
                logger.info('New top: %s' % str(db_refs['WM'][idx]))
            db_refs['WM'] = db_refs['WM'][idx:]

    logger.info('Removing intervention groundings from non-Hume statements.')
    for stmt in stmts:
        sg = get_grounding(stmt.subj)
        og = get_grounding(stmt.obj)
        if stmt.evidence[0].source_api != 'hume':
            if is_intervention(sg[0]):
                remove_top_interventions(stmt.subj.concept.db_refs)
            if is_intervention(og[0]):
                remove_top_interventions(stmt.obj.concept.db_refs)
    return stmts


def filter_out_long_words(stmts, k=10):
    logger.info(f'Filtering to concepts with max {k} words on {len(stmts)}'
                f' statements.')

    def get_text(ag):
        return ag.concept.db_refs['TEXT']

    def text_too_long(txt, k):
        if len(txt.split()) > k:
            return True
        return False

    new_stmts = []
    for stmt in stmts:
        st = get_text(stmt.subj)
        ot = get_text(stmt.obj)
        if text_too_long(st, k) or text_too_long(ot, k):
            continue
        new_stmts.append(stmt)
    logger.info(f'{len(new_stmts)} statements after filter.')
    return new_stmts


if __name__ == '__main__':
    wm_ont = load_world_ontology(wm_ont_url)

    # Load all raw statements
    eidos_stmts = load_eidos()
    eidos_stmts = ac.filter_by_type(eidos_stmts, Influence)
    hume_stmts = load_hume()
    hume_stmts = ac.filter_by_type(hume_stmts, Influence)
    hume_stmts = remove_hume_redundant(hume_stmts, None)
    #sofia_stmts = load_sofia()
    #cwms_stmts = load_cwms()

    # Reground where needed
    # sofia_stmts = reground_stmts(sofia_stmts, wm_ont, 'WM')
    # cwms_stmts = reground_stmts(cwms_stmts, wm_ont, 'WM')

    # Put statements together and filter to influence
    #stmts = eidos_stmts + hume_stmts + sofia_stmts + cwms_stmts
    stmts = eidos_stmts + hume_stmts
    # Remove name spaces that aren't needed in CauseMos
    remove_namespaces(stmts, ['WHO', 'MITRE12', 'UN'])

    stmts = ac.filter_grounded_only(stmts, score_threshold=0.7)
    #stmts = filter_to_hume_interventions_only(stmts)
    # Filter again to remove any new top level groundings after
    # previous step.
    #stmts = ac.filter_grounded_only(stmts, score_threshold=0.7)
    stmts = filter_out_long_words(stmts, 10)
    stmts = filter_groundings(stmts)
    # Make sure we don't include context before 1900
    stmts = filter_context_date(stmts, from_date=datetime(1900, 1, 1))
    stmts = set_positive_polarities(stmts)

    scorer = get_eidos_scorer()

    funs = {
        'grounding': (None, None),
        #'location': (location_matches, location_refinement),
        #'location_and_time': (location_time_matches,
        #                      location_time_refinement)
    }

    meta_data = {'description':
       'This corpus was generated based on output '
       'from Eidos and Hume before the 2020 Spring WM PI meeting '
       'to assess the quality of intervention grounding.',
       'readers': ['hume', 'eidos'],
       'date': '2020-03-13',
       'assembly': {
           'level': None,
           'grounding_threshold': 0.7,
           }}

    for key, (matches_fun, refinement_fun) in funs.items():
        assembled_stmts = ac.run_preassembly(stmts,
                                             belief_scorer=scorer,
                                             matches_fun=matches_fun,
                                             refinement_fun=refinement_fun,
                                             normalize_equivalences=True,
                                             normalize_opposites=True,
                                             normalize_ns='WM',
                                             ontology=wm_ont,
                                             return_toplevel=False,
                                             poolsize=16)
        print_statistics(assembled_stmts)
        remove_raw_grounding(assembled_stmts)
        corpus = Corpus(assembled_stmts, raw_statements=stmts,
                        meta_data=meta_data)
        corpus_name = 'dart-20200313-interventions-%s' % key
        corpus.s3_put(corpus_name)
        meta_data['assembly']['level'] = key
        sj = stmts_to_json(assembled_stmts, matches_fun=matches_fun)
        with open(os.path.join(data_path, corpus_name + '.json'), 'w') as fh:
            json.dump(sj, fh, indent=1)
