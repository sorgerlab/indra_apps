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

    def get_location(stmt):
        if not has_location(stmt):
            loc = None
        else:
            loc = stmt.context.geo_location.db_refs['GEOID']
        return loc

    def get_time(stmt):
        if not has_time(stmt):
            time = None
        else:
            time = stmt.context.time
        return time

    def location_matches(stmt):
        if isinstance(stmt, Event):
            context_key = get_location(stmt)
            matches_key = str((stmt.concept.matches_key(), context_key))
        if isinstance(stmt, Influence):
            subj_context_key = get_location(stmt.subj)
            obj_context_key = get_location(stmt.obj)
            matches_key = str(stmt.matches_key(), subj_context_key,
                              obj_context_key)
        else:
            matches_key = stmt.matches_key()
        return matches_key

    def event_location_refinement(st1, st2, hierarchies):
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

    def location_refinement(st1, st2, hierarchies):
        type(st1) != type(st2):
            return False
        if isinstance(st1, Event):
            event_ref = event_location_refinement(st1, st2, hierarchies)
            return event_ref
        elif isinstance(st1, Influence):
            subj_ref = event_location_refinement(st1.subj, st2.subj,
                                                 hierarchies)
            obj_ref = event_location_refinement(st1.obj, st2.obj,
                                                hierarchies)
            return subj_ref and obj_ref
        else:
            return st1.refinement_of(st2, hierarchies)


    def event_location_time_matches(event):
        mk = location_matches(event)
        if not has_time(event):
            return mk
        time = get_time(stmt)
        matches_key = str((mk, time.start, time.end, time.duration))
        return matches_key


    def location_time_matches(stmt):
        if isinstance(stmt, Event):
            return event_location_time_matches(stmt)
        elif isinstance(stmt, Influence):
            subj_mk = event_location_time_matches(stmt.subj)
            obj_mk = event_location_time_matches(stmt.obj)
            return str((stmt.matches_key(), subj_mk, obj_mk))
        else:
            return stmt.matches_key()

    def event_location_time_refinement(st1, st2, hierarchies):
        ref = location_refinement(st1, st2, hierarchies)
        if not ref:
            return False
        if not has_time(st2):
            return True
        elif not has_time(st1) :
            return False
        else:
            return st1.context.time.refinement_of(st2.context.time)

    def location_time_refinement(st1, st2, hierarchies):
        if type(st1) != type(st2):
            return False
        if isinstance(st1, Event):
            return event_location_time_refinement(st1, st2, hierarchies)
        elif isinstance(st1, Influence):
            ref = st1.refinement_of(st2, hierarchies)
            if not ref:
                return False
            subj_ref = event_location_time_refinement(st1.subj, st2.subj,
                                                      hierarchies)
            obj_ref = event_location_time_refinement(st1.obj, st2.obj,
                                                     hierarchies)
            return subj_ref and obj_ref
    funs = {
        'grounding': (None, None),
        'location': (location_matches, location_refinement),
        'location_and_time': (location_time_matches,
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
