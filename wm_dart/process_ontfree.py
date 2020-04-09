from process import *
from collections import Counter
from indra.preassembler.custom_preassembly import agent_name_stmt_type_matches


def norm_name(name):
    return '_'.join(sorted(list(set(name.lower().split()))))


def make_fake_wm(stmts):
    for stmt in stmts:
        for agent in stmt.agent_list():
            agent.db_refs['WM'] = [(norm_name(agent.name), 1.0)]


def filter_name_frequency(stmts, k=2):
    norm_names = []
    for stmt in stmts:
        for agent in stmt.agent_list():
            norm_names.append(norm_name(agent.name))
    cnt = Counter(norm_names)
    names = {n for n, c in cnt.most_common() if c >= k}

    new_stmts = []
    for stmt in stmts:
        found = True
        for agent in stmt.agent_list():
            if norm_name(agent.name) not in names:
                found = False
                break
        if found:
            new_stmts.append(stmt)
    return new_stmts


if __name__ == '__main__':
    stmts = load_eidos()
    make_fake_wm(stmts)
    stmts = filter_name_frequency(stmts, k=2)
    assembled_stmts = ac.run_preassembly(stmts,
                                         matches_fun=agent_name_stmt_type_matches)
    corpus_name = 'dart-20200127-ontfree-2'
    corpus = Corpus(corpus_name, assembled_stmts, raw_statements=stmts)
    corpus.s3_put(corpus_name)
