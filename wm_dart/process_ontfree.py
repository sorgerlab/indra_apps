from process import *
from indra.preassembler.custom_preassembly import agent_name_stmt_type_matches


def make_fake_wm(stmts):
    for stmt in stmts:
        for agent in stmt.agent_list():
            norm_name = sorted(list(set(agent.name.split())))
            agent.db_refs['WM'] = [('_'.join(norm_name), 1.0)]


stmts = load_eidos()
make_fake_wm(stmts)
assembled_stmts = ac.run_preassembly(stmts,
                                     matches_fun=agent_name_stmt_type_matches)
corpus = Corpus(assembled_stmts, raw_statements=stmts)
corpus_name = 'dart-20200127-ontfree-%s' % key
corpus.s3_put(corpus_name)
