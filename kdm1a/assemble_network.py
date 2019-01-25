from indra.statements import *
from itertools import combinations


# Fix groundings (db_refs) of Agents in Statements
stmts = ac.map_grounding(stmts)
# Filter out any Statements that have ungrounded Agent
stmts = ac.filter_grounded_only(stmts)
# Filter out non-human proteins/genes
stmts = ac.filter_human_only(stmts)
# Expand families optionally
# e.g. turn MEK into MAP2K1 and MAP2K2 and expand Statements combinatorially
# stmts = ac.expand_families(stmts)
# Fix references to incorrect amino acid sites
stmts = ac.map_sequence(stmts)
# Run preassembly
stmts = ac.run_preassembly(stmts, return_toplevel=False, poolsize=4)
stmts = ac.filter_belief(stmts, 0.85)
stmts = ac.filter_top_level(stmts)
# If you want to, you can try to filter out things that are not direct
# stmts = ac.filter_direct(stmts)


def get_stmts_by_matches_key(stmts, key):
    stmts_for_matches_key = []
    for stmt in stmts:
        for agent in stmt.agent_list():
            if agent is not None:
                agent_key = agent.matches_key()
                if agent_key == key:
                    stmts_for_matches_key.append(stmt)
    return stmts_for_matches_key


class X(object):
    def __init__(self):
        self.statements = [Complex([Agent('a'), Agent('b')])]

    def MG_from_INDRA(self):
        for stmt in self.stmts:
            stmt_type = type(stmt).__name__
            # Get all agents in the statement
            agents = stmt.agent_list()
            # Filter out None Agent
            agents = [a for a in agents if a is not None]
            # Only include edges for statements with at least 2 Agents
            if len(agents) < 2:
                continue
            edge_attrs = {'type': stmt_type,
                          'uuid': stmt.uuid}
            # Iterate over all the agent combinations and add edge
            for a, b in combinations(agents, 2):
                self._add_Inode_edge(a, b, edge_attrs)
