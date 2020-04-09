import json
import glob
import copy
from indra.sources import eidos
from indra.tools.live_curation import Corpus
from indra.tools import assemble_corpus as ac
from indra.belief.wm_scorer import get_eidos_scorer
from indra.preassembler.custom_preassembly import *
from indra.statements import Event, Influence, Association

# For 52-document corpus
# fnames = glob.glob('jsonld-merged20190404/*.jsonld')

# For 500-document corpus
# Extracted from https://drive.google.com/drive/folders/
# 1CrGfVYaZg_O13YojYSlWbhpSuXKQjHMq,  Doc500BMost1.zip
fnames = glob.glob('mitre500-20190721/jsonld/*.jsonld')


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


def fix_provenance(stmts):
    """Move the document identifiers in evidences."""
    for stmt in stmts:
        for ev in stmt.evidence:
            prov = ev.annotations['provenance'][0]['document']
            if 'title' in prov:
                prov['@id'] = prov.pop('title', None)


def check_event_context(events):
    for event in events:
        if not event.context and event.evidence[0].context:
            assert False, ('Event context issue', event, event.evidence)
        ej = event.to_json()
        if 'context' not in ej and 'context' in ej['evidence'][0]:
            assert False, ('Event context issue', event, event.evidence)


if __name__ == '__main__':
    stmts = []
    for fname in fnames:
        print('Processing %s' % fname)
        ep = eidos.process_json_file(fname)
        stmts += ep.statements
    remove_namespaces(stmts, ['WHO', 'MITRE12'])

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

    for key, (matches_fun, refinement_fun) in funs.items():
        assembled_non_events = ac.run_preassembly(non_events,
                                                  belief_scorer=scorer,
                                                  matches_fun=matches_fun,
                                                  refinement_fun=refinement_fun)
        assembled_events = ac.run_preassembly(events, belief_scorer=scorer,
                                    matches_fun=matches_fun,
                                    refinement_fun=refinement_fun)
        check_event_context(assembled_events)
        assembled_stmts = assembled_non_events + assembled_events
        remove_raw_grounding(assembled_stmts)
        fix_provenance(assembled_stmts)
        corpus_id='mitre500-20190721-stmts-%s' % key
        corpus = Corpus(corpus_id, assembled_stmts, raw_statements=stmts)
        corpus.s3_put()
        sj = stmts_to_json(assembled_stmts, matches_fun=matches_fun)
        with open('%s.json' % corpus_id, 'w') as fh:
            json.dump(sj, fh, indent=1)
