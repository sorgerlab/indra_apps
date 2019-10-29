from indra.util import _require_python3
from indra.assemblers.sif import SifAssembler
import indra.tools.assemble_corpus as ac

stmts = ac.load_statements('output/preassembled.pkl')
stmts = ac.filter_belief(stmts, 0.95)
stmts = ac.filter_direct(stmts)
sa = SifAssembler(stmts)
sa.make_model(True, True, False)
sa.set_edge_weights('support_all')
fname = 'model_high_belief_v2.sif'
with open(fname, 'wt') as fh:
    for s, t, d in sa.graph.edges(data=True):
        source = sa.graph.nodes[s]['name']
        target = sa.graph.nodes[t]['name']
        fh.write('%s %f %s\n' % (source, d['weight'], target))
