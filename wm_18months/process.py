import json
import glob
import copy
from indra.sources import eidos
from indra.tools import assemble_corpus as ac
from indra.belief.wm_scorer import get_eidos_scorer
from indra.preassembler.custom_preassembly import *
from indra.tools.live_curation import Corpus

fnames = glob.glob('jsonld-merged20190404/*.jsonld')


def get_events(stmts):
    # Create list of standalone events
    events = []
    for stmt in stmts:
        if isinstance(stmt, Influence):
            for member in [stmt.subj, stmt.obj]:
                member.evidence = stmt.evidence[:]
                events.append(member)
        elif isinstance(stmt, Association):
            for member in stmt.members:
                member.evidence = stmt.evidence[:]
                events.append(member)
        elif isinstance(stmt, Event):
            events.append(stmt)
    return events


def get_non_events(stmts):
    return [st for st in stmts if not isinstance(st, Event)]


def remove_namespaces(stmts, namespaces):
    for stmt in stmts:
        for agent in stmt.agent_list():
            for namespace in namespaces:
                if namespace in copy.deepcopy(agent.db_refs):
                    agent.db_refs.pop(namespace, None)


def remove_raw_grounding(stmts):
    for stmt in stmts:
        for ev in stmt.evidence:
            if not ev.annotations:
                continue
            agents = ev.annotations.get('agents')
            if not agents:
                continue
            if 'raw_grounding' in agents:
                agents.pop('raw_grounding', None)


if __name__ == '__main__':
    stmts = []
    for fname in fnames:
        ep = eidos.process_json_file(fname)
        stmts += ep.statements
    remove_namespaces(stmts, ['WHO', 'MITRE12'])

    events = get_events(stmts)
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
        assembled_stmts = assembled_non_events + assembled_events
        remove_raw_grounding(assembled_stmts)
        corpus = Corpus(assembled_stmts, raw_statements=stmts)
        corpus.s3_put('jsonld-merged20190627-stmts-%s' % key)
        sj = stmts_to_json(assembled_stmts, matches_fun=matches_fun)
        with open('jsonld-merged20190627-stmts-%s.json' % key, 'w') as fh:
            json.dump(sj, fh, indent=1)
