import json
import glob
from indra.sources import eidos
from indra.tools import assemble_corpus as ac
from indra.statements import stmts_to_json, Influence, Event
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
            events += [stmt.subj, stmt.obj]
        elif isinstance(stmt, Association):
            events += stmt.members
        elif isinstance(stmt, Event):
            events.append(stmt)

    scorer = get_eidos_scorer()

    assembled_stmts = ac.run_preassembly(stmts, belief_scorer=scorer)
    assembled_events = ac.run_preassembly(events, belief_scorer=scorer)
    sj = stmts_to_json(assembled_stmts)
    with open('jsonld-merged20190607-stmts.json', 'w') as fh:
        json.dump(sj, fh, indent=1)

    ej = stmts_to_json(assembled_events)
    with open('jsonld-merged20190607-events.json', 'w') as fh:
        json.dump(ej, fh, indent=1)
