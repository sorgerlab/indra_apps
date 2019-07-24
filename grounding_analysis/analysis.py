import sys
from collections import Counter
from indra.statements import Complex
from indra.sources import indra_db_rest


def get_statements(db_ns, db_id, ev_limit=100):
    ip = indra_db_rest.get_statements(agents=['%s@%s' % (db_id, db_ns)],
                                      ev_limit=ev_limit)
    return ip.statements


def get_raw_strings(stmts, db_ns, db_id):
    raw_strings = []
    for stmt in stmts:
        # Raw annotations for Complexes are not reliable
        # due to possible reordering
        if isinstance(stmt, Complex):
            continue
        for idx, agent in enumerate(stmt.agent_list()):
            if agent is not None and agent.db_refs.get(db_ns) == db_id:
                for ev in stmt.evidence:
                    agents = ev.annotations['agents']
                    text = agents['raw_text'][idx]
                    if text:
                        raw_strings.append(text)
    return raw_strings


def get_top_counts(raw_strings, threshold=0.8):
    cnt = Counter(raw_strings)
    ranked_list = cnt.most_common()
    total = sum(c for e, c in ranked_list)
    top_list = []
    cum_sum = 0
    for element, count in ranked_list:
        cum_sum += (count / total)
        top_list.append((element, count))
        if cum_sum >= threshold:
            break
    return top_list


if __name__ == '__main__':
    db_ns, db_id = sys.argv[1], sys.argv[2]
    stmts = get_statements(db_ns, db_id)
    raw_strings = get_raw_strings(stmts, db_ns, db_id)
    top_list = get_top_counts(raw_strings)
    print(top_list)
