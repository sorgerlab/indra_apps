from collections import defaultdict
from indra.tools.assemble_corpus import merge_groundings

def surface_context(stmt):
    time_contexts = []
    loc_contexts = []
    for ev in stmt.evidence:
        if ev.context:
            tc = ev.context.time if ev.context.time else None
            time_contexts.append(tc)
            gc = ev.context.geo_location if ev.context.geo_location else None
            loc_contexts.append(gc)
    if len(time_contexts) > 1:
        print(time_contexts)
        print(loc_contexts)
