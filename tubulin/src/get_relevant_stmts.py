import csv
from collections import defaultdict, Counter
import networkx as nx
from indra.db import client
from indra.databases import hgnc_client
from indra.statements import *
from indra.tools import assemble_corpus as ac
from indra.tools.expand_families import Expander
from indra.preassembler.hierarchy_manager import hierarchies
from paths_graph import PathsGraph, CombinedPathsGraph, get_reachable_sets

from matplotlib import pyplot as plt

def get_phosphorylation_stmts(residue_file):
    # Load the sites from the file
    sites = defaultdict(list)
    with open(residue_file, 'rt') as f:
        csvreader = csv.reader(f, delimiter=',')
        for gene, site in csvreader:
            sites[gene].append(site)
    # Get phosphorylation stmts for the sites
    stmts = []
    counter = 0
    for gene, res_list in sites.items():
        print("%d of %d: getting Phosphorylation statements for %s" %
              (counter, len(sites), gene))
        phos_stmts = client.get_statements_by_gene_role_type(
                agent_id=gene, role='OBJECT', stmt_type='Phosphorylation')
        for ps in phos_stmts:
            if ps.enz is not None and ps.position in res_list:
                stmts.append(ps)
        counter += 1
    return stmts


def get_stmt_subject_object(stmts, type):
    if type not in ['SUBJECT', 'OBJECT']:
        raise ValueError('type must be one of (SUBJECT, OBJECT)')
    stmt_agents = set()
    for stmt in stmts:
        assert len(stmt.agent_list()) == 2
        if type == 'SUBJECT':
            ag = stmt.agent_list()[0]
        else:
            ag = stmt.agent_list()[1]
        # Get HGNC and FPLX groundings, preferring HGNC to FPLX IDs
        # Other types of nodes (chemicals, biological processes, etc.) are
        # currently ignored
        # TODO: Include ungrounded agents (with only 'TEXT' in db_refs)
        if 'HGNC' in ag.db_refs:
            stmt_agents.add(('HGNC',
                             hgnc_client.get_hgnc_name(ag.db_refs['HGNC'])))
        elif 'FPLX' in ag.db_refs:
            stmt_agents.add(('FPLX', ag.db_refs['FPLX']))
    return stmt_agents


def get_network_stmts(source_list, target_list, max_depth):
    # Look at successors first
    f_level = {0: set(source_list)}
    b_level = {0: set(target_list)}
    fwd_stmts = []
    for i in range(1, max_depth+1):
        import ipdb; ipdb.set_trace()
        reachable_agents = set()
        for ag_ns, ag_id in f_level[i-1]:
            if ag_ns == 'HGNC':
                ag_ns = 'HGNC-SYMBOL'
            succ_stmts = client.get_statements_by_gene_role_type(
                    agent_ns=ag_ns, agent_id=ag_id, role='SUBJECT')
            succ_stmts = ac.filter_by_type(succ_stmts, Complex, invert=True)
            succ_stmts = ac.filter_by_type(succ_stmts, SelfModification,
                                                invert=True)
            fwd_stmts.extend(succ_stmts)
            # Get succ nodes
            succ_agents = get_stmt_subject_object(succ_stmts, 'OBJECT')
            reachable_agents |= succ_agents
            # For the next level we only need to include the agents that we
            # didn't already have at this level
        f_level[i] = reachable_agents.difference(f_level[i-1])
    return f_level, fwd_stmts


def get_kinase_counts(stmts):
    """Given a set of Phosphorylation statements returns the list of kinases.
    """
    kinases = [s.enz.name for s in stmts]
    kin_ctr = Counter(kinases)
    kin_ctr = sorted([(k, v) for k, v in kin_ctr.items()],
                     key=lambda x: x[1], reverse=True)
    return kin_ctr


def load_stmt_graph(filename):
    # Load edges from the graph file
    raw_edges = defaultdict(list)
    with open(filename, 'rt') as f:
        csvreader = csv.reader(f, delimiter='\t')
        for subject, object, type, stmt_hash in csvreader:
            raw_edges[(subject, object)].append(stmt_hash)
    # Flatten the edge list into a data dictionary
    edges = []
    for edge, hash_list in raw_edges.items():
        u, v = edge
        edges.append((u, v, {'hash_list': hash_list}))
    # Add edges to graph
    graph = nx.DiGraph()
    graph.add_edges_from(edges)
    return graph


def draw(g, filename):
    ag = nx.nx_agraph.to_agraph(g)
    ag.draw(filename, prog='dot')


def get_stmt_hashes_from_pg(graph, pg):
    stmt_hashes = set()
    for u, v in pg.graph.edges():
        _, u_name = u
        _, v_name = v
        if u_name == 'SOURCE' or v_name == 'TARGET':
            continue
        stmt_hashes |= set(graph[u_name][v_name]['hash_list'])
    return stmt_hashes

if __name__ == '__main__':
    reload = False
    if reload:
        phos_stmts = \
                get_phosphorylation_stmts('../work/genes_with_residues.csv')
        ac.dump_statements(phos_stmts, '../work/phospho_stmts.pkl')
    else:
        phos_stmts = ac.load_statements('../work/phospho_stmts.pkl')

    #kinases = get_kinase_counts(phos_stmts)

    target_list = get_stmt_subject_object(phos_stmts, 'SUBJECT')

    # Get all Tubulin child nodes as the source list
    source_list = [('FPLX', 'Tubulin')]
    tubulin_ag = Agent('Tubulin', db_refs={'FPLX': 'Tubulin'})
    ex = Expander(hierarchies)
    for ag_ns, ag_id in ex.get_children(tubulin_ag, ns_filter=None):
        #if ag_ns == 'HGNC':
        #    ag_id = hgnc_client.get_hgnc_id(ag_id)
        source_list.append((ag_ns, ag_id))

    # Add a dummy source
    graph_file = '../input/july_2018_pa_HGNC_FPLX_typed_directional_pairs.tsv'
    graph = load_stmt_graph(graph_file)
    dummy_edges = [('SOURCE', src[1]) for src in source_list]
    dummy_edges += [(tgt[1], 'TARGET') for tgt in target_list]
    graph.add_edges_from(dummy_edges)

    #result = get_network_stmts(source_list, target_list, max_depth=2)

    max_depth = 8
    pg_list = []
    lengths = []
    stmt_counts = []
    f_level, b_level = get_reachable_sets(graph, 'SOURCE', 'TARGET', max_depth)
    for length in range(3, max_depth+1):
        pg = PathsGraph.from_graph(graph, 'SOURCE', 'TARGET', length,
                                   fwd_reachset=f_level, back_reachset=b_level)

        stmt_hashes = get_stmt_hashes_from_pg(graph, pg)
        print("%d stmts for paths of length %d" %
              (len(stmt_hashes), length - 2))
        pg_list.append(pg)
        lengths.append(length - 2)
        stmt_counts.append(len(stmt_hashes))
    plt.ion()
    plt.plot(lengths, stmt_hashes)
    ax = plt.gca()
    ax.set_yscale('log')
