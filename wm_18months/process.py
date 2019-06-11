import json
import glob
from indra.sources import eidos
from indra.tools import assemble_corpus as ac
from indra.statements import stmts_to_json, Influence, Event, Association
from indra.belief.wm_scorer import get_eidos_scorer

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

    def has_location(stmt):
        if not stmt.context or not stmt.context.geo_location or \
                not stmt.context.geo_location.db_refs.get('GEOID'):
            return False
        return True

    def has_time(stmt):
        if not stmt.context or not stmt.context.time:
            return False
        return True

    def event_location_matches(stmt):
        if isinstance(stmt, Event):
            if not has_location(stmt):
                context_key = None
            else:
                context_key = stmt.context.geo_location.db_refs['GEOID']

            matches_key = str((stmt.concept.matches_key(), context_key))
        else:
            matches_key = stmt.matches_key()
        return matches_key

    def event_location_refinement(st1, st2, hierarchies):
        if isinstance(st1, Event) and isinstance(st2, Event):
            ref = st1.refinement_of(st2, hierarchies)
            if not ref:
                return False
            if not has_location(st2):
                return True
            elif not has_location(st1):
                return False
            else:
                return st1.context.geo_location.db_refs['GEOID'] == \
                       st2.context.geo_location.db_refs['GEOID']

    def event_location_time_matches(stmt):
        mk = event_location_matches(stmt)
        if not has_time(stmt):
            return mk
        matches_key = str((mk, stmt.context.time.start,
                           stmt.context.time.end,
                           stmt.context.time.duration))
        return matches_key

    def event_location_time_refinement(st1, st2, hierarchies):
        ref = event_location_refinement(st1, st2, hierarchies)
        if not ref:
            return False
        if not has_time(st2):
            return True
        elif not has_time(st1) :
            return False
        else:
            return st1.context.time.refinement_of(st2.context.time)


    funs = {
        'grounding': (None, None),
        'location': (event_location_matches, event_location_refinement),
        'location_and_time': (event_location_time_matches,
                              event_location_time_refinement)
        }

    for key, (matches_fun, refinement_fun) in funs.items():
        assembled_stmts = ac.run_preassembly(stmts, belief_scorer=scorer)
        assembled_events = ac.run_preassembly(events, belief_scorer=scorer,
                                    matches_fun=matches_fun,
                                    refinement_fun=refinement_fun)
        sj = stmts_to_json(assembled_stmts)
        with open('jsonld-merged20190609-stmts-%s.json' % key, 'w') as fh:
            json.dump(sj, fh, indent=1)

        ej = stmts_to_json(assembled_events)
        with open('jsonld-merged20190609-events-%s.json' % key, 'w') as fh:
            json.dump(ej, fh, indent=1)
