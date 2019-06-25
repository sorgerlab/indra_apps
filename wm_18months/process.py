import json
import glob
from indra.sources import eidos
from indra.tools import assemble_corpus as ac
from indra.belief.wm_scorer import get_eidos_scorer
from indra.preassembler.custom_preassembly import *

fnames = glob.glob('jsonld-merged20190404/*.jsonld')


if __name__ == '__main__':
    stmts = []
    for fname in fnames:
        ep = eidos.process_json_file(fname)
        stmts += ep.statements

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

    scorer = get_eidos_scorer()

    funs = {
        'grounding': (None, None),
        'location': (location_matches, location_refinement),
        'location_and_time': (location_time_matches,
                              location_time_refinement)
        }

    for key, (matches_fun, refinement_fun) in funs.items():
        assembled_stmts = ac.run_preassembly(stmts, belief_scorer=scorer)
        assembled_events = ac.run_preassembly(events, belief_scorer=scorer,
                                    matches_fun=matches_fun,
                                    refinement_fun=refinement_fun)
        sj = stmts_to_json(assembled_stmts)
        with open('jsonld-merged20190611-stmts-%s.json' % key, 'w') as fh:
            json.dump(sj, fh, indent=1)

        ej = stmts_to_json(assembled_events)
        with open('jsonld-merged20190611-events-%s.json' % key, 'w') as fh:
            json.dump(ej, fh, indent=1)
