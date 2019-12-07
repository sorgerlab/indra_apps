import os
import glob
import copy
import tqdm
import json
import yaml
import pickle
import logging
import argparse
import requests
from datetime import datetime
from indra.sources import eidos, hume, sofia, cwms
from indra.sources.eidos import migration_table_processor
from indra.tools.live_curation import Corpus
from indra.tools import assemble_corpus as ac
from indra.sources.eidos.reader import EidosReader
from indra.belief.wm_scorer import get_eidos_scorer
from indra.preassembler.custom_preassembly import *
from indra.statements import Event, Influence, Association
from indra.preassembler.hierarchy_manager import YamlHierarchyManager, \
    get_wm_hierarchies
from indra.preassembler.make_wm_ontologies import eidos_ont_url, \
    load_yaml_from_url, rdf_graph_from_yaml, wm_ont_url

import indra
indra.logger.setLevel(logging.DEBUG)

logger = logging.getLogger()
#data_path = os.path.join(os.path.expanduser('~'), 'data', 'wm', 'dart')
data_path = os.path.join('.', 'data')


def load_eidos():
    logger.info('Loading Eidos statements')
    fnames = glob.glob(os.path.join(data_path, 'eidos/jsonldDir/*.jsonld'))

    stmts = []
    for fname in tqdm.tqdm(fnames):
        doc_id = os.path.basename(fname).split('.')[0]
        ep = eidos.process_json_file(fname)
        fix_provenance(ep.statements, doc_id)
        stmts += ep.statements
    logger.info(f'Loaded {len(stmts)} statements from Eidos')
    return stmts


def load_hume(cached=True):
    logger.info('Loading Hume statements')
    pkl_name = os.path.join(data_path, 'hume', 'stmts.pkl')
    if cached:
        if os.path.exists(pkl_name):
            with open(pkl_name, 'rb') as fh:
                stmts = pickle.load(fh)
                return stmts
    fnames = glob.glob(os.path.join(data_path, 'hume', '*.json-ld'))

    stmts = []
    for fname in tqdm.tqdm(fnames):
        hp = hume.process_jsonld_file(fname)
        stmts += hp.statements
    logger.info(f'Loaded {len(stmts)} statements from Hume')
    with open(pkl_name, 'wb') as fh:
        pickle.dump(stmts, fh)
    return stmts


def load_cwms(cached=True):
    pkl_name = os.path.join(data_path, 'cwms', 'stmts.pkl')
    if cached:
        if os.path.exists(pkl_name):
            with open(pkl_name, 'rb') as fh:
                stmts = pickle.load(fh)
                return stmts
    logger.info('Loading CWMS statements')
    fnames = glob.glob(os.path.join(data_path, 'cwms', 'ekbs', '*.ekb'))
    stmts = []
    for fname in tqdm.tqdm(fnames):
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


def load_sofia():
    logger.info('Loading Sofia statements')
    fnames = glob.glob(os.path.join(data_path,
                                    'sofia/Nov_*.xlsx'))

    stmts = []
    doc_ids = set()
    for idx, fname in enumerate(fnames):
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
    return stmts


def load_migration_spreadsheets(sheets_path):
    sheets_path = sheets_path if sheets_path.endswith('/') else \
        sheets_path + '/'
    spreadsheets = glob.glob(sheets_path + '*.xlsx')
    ms = []
    for sheet in spreadsheets:
        ms += migration_table_processor.process_workbook(sheet)
    return ms

def fix_provenance(stmts, doc_id):
    """Move the document identifiers in evidences."""
    for stmt in stmts:
        for ev in stmt.evidence:
            prov = ev.annotations['provenance'][0]['document']
            prov['@id'] = doc_id


def remove_namespaces(stmts, namespaces):
    """Remove unnecessary namespaces from Concept grounding."""
    for stmt in stmts:
        for agent in stmt.agent_list():
            for namespace in namespaces:
                if namespace in copy.deepcopy(agent.db_refs):
                    agent.db_refs.pop(namespace, None)


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


def reground_stmts(stmts, eidos_reader, ont_manager, namespace):
    # Send the latest ontology and list of concept texts to Eidos
    yaml_str = yaml.dump(ont_manager.yaml_root)
    concepts = []
    for stmt in stmts:
        for concept in stmt.agent_list():
            concept_txt = concept.db_refs.get('TEXT')
            concepts.append(concept_txt)
    groundings = eidos_reader.reground_texts(concepts, yaml_str)
    # Update the corpus with new groundings
    idx = 0
    for stmt in stmts:
        for concept in stmt.agent_list():
            if groundings[idx] and namespace not in concept.db_refs:
                concept.db_refs[namespace] = groundings[idx]
            idx += 1
    return stmts


def _make_un_ontology():
    return YamlHierarchyManager(load_yaml_from_url(eidos_ont_url),
                                rdf_graph_from_yaml, True)


def _make_wm_ontology():
    return YamlHierarchyManager(load_yaml_from_url(wm_ont_url),
                                rdf_graph_from_yaml, True)


def filter_dart_date(stmts, datestr):
    res = get_all_dart_resources()
    fres = filter_dart_sources(res, datestr, before=True)
    ids = {h['_id'] for h in fres['hits']['hits']}

    logger.info(f'Filtering {len(stmts)} statements with {len(ids)} DART IDs')
    stmts = [s for s in stmts if
             (s.evidence[0].annotations['provenance'][0]['document']['@id']
              in ids)]
    logger.info(f'{len(stmts)} statements after filter')
    return stmts


def fix_wm_ontology(stmts):
    for stmt in stmts:
        for concept in stmt.agent_list():
            if 'WM' in concept.db_refs:
                concept.db_refs['WM'] = [(entry.replace(' ', '_'), score)
                                         for entry, score in
                                         concept.db_refs['WM']]
                concept.db_refs['WM'] = [(entry.replace('boarder', 'border'),
                                          score)
                                         for entry, score in
                                         concept.db_refs['WM']]


def print_statistics(stmts):
    ev_tot = sum([len(stmt.evidence) for stmt in stmts])
    logger.info(f'Total evidence {ev_tot} for {len(stmts)} statements.')


if __name__ == '__main__':
    wm_ont = _make_wm_ontology()
    eidos_reader = EidosReader()
    parser = argparse.ArgumentParser()
    parser.add_argument('--spreadsheets-path', type=str)
    args = parser.parse_args()

    sofia_stmts = load_sofia()
    sofia_stmts = reground_stmts(sofia_stmts, eidos_reader, wm_ont, 'WM')
    # mig_stmts = load_migration_spreadsheets(args.spreadsheet_path)
    eidos_stmts = load_eidos()
    hume_stmts = load_hume()
    cwms_stmts = load_cwms()
    cwms_stmts = reground_stmts(cwms_stmts, eidos_reader, wm_ont, 'WM')
    stmts = eidos_stmts + hume_stmts + sofia_stmts + cwms_stmts # + mig_stmts
    stmts = ac.filter_by_type(stmts, Influence)
    remove_namespaces(stmts, ['WHO', 'MITRE12', 'UN'])

    events = get_events(stmts)
    check_event_context(events)
    non_events = get_non_events(stmts)
    scorer = get_eidos_scorer()

    funs = {
        'grounding': (None, None),
        'location': (location_matches, location_refinement),
        'location_and_time': (location_time_matches,
                              location_time_refinement)
    }

    hierarchies = get_wm_hierarchies()

    for key, (matches_fun, refinement_fun) in funs.items():
        assembled_non_events = ac.run_preassembly(non_events,
                                                  belief_scorer=scorer,
                                                  matches_fun=matches_fun,
                                                  refinement_fun=refinement_fun,
                                                  normalize_equivalences=True,
                                                  normalize_opposites=True,
                                                  normalize_ns='WM',
                                                  hierarchies=hierarchies,
                                                  return_toplevel=False,
                                                  poolsize=16)
        print_statistics(assembled_non_events)
        logger.info('-----Finished assembly-----')
        assembled_events = ac.run_preassembly(events, belief_scorer=scorer,
                                              matches_fun=matches_fun,
                                              refinement_fun=refinement_fun,
                                              normalize_equivalences=True,
                                              normalize_opposites=True,
                                              normalize_ns='WM',
                                              hierarchies=hierarchies,
                                              return_toplevel=False,
                                              poolsize=16)
        logger.info('-----Finished assembly-----')
        print_statistics(assembled_events)
        check_event_context(assembled_events)
        assembled_stmts = assembled_non_events + assembled_events
        remove_raw_grounding(assembled_stmts)
        corpus = Corpus(assembled_stmts, raw_statements=stmts)
        corpus_name = 'dart-20191016-stmts-%s' % key
        corpus.s3_put(corpus_name)
        sj = stmts_to_json(assembled_stmts, matches_fun=matches_fun)
        with open(os.path.join(data_path, corpus_name + '.json'), 'w') as fh:
            json.dump(sj, fh, indent=1)
