import csv
from collections import defaultdict, Counter
import networkx as nx
from indra_db import client
from indra.databases import hgnc_client
from indra.statements import *
from indra.tools import assemble_corpus as ac
from indra.tools.expand_families import Expander
from indra.ontology.bio import bio_ontology
from paths_graph import PathsGraph, CombinedPathsGraph, get_reachable_sets


def get_phosphorylation_stmts(residue_file):
    # Load the sites from the file
    sites = defaultdict(list)
    with open(residue_file, 'rt') as f:
        csvreader = csv.reader(f, delimiter='\t')
        next(csvreader) # Skip the header row
        for gene_site, _ in csvreader:
            gene, site = gene_site.split('_')
            residue = site[0]
            position = site[1:]
            sites[gene].append(position)
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


def regulons_from_stmts(stmts, filename):
    regulons = defaultdict(set)
    stmts = ac.filter_genes_only(stmts)
    stmts = ac.filter_human_only(stmts)
    for stmt in stmts:
        kinase = stmt.enz.name
        # Blacklist annoying stmts from NCI-PID
        if (kinase == 'BRAF' or kinase == 'RAF1') and \
           (stmt.sub.name == 'MAPK1' or stmt.sub.name == 'MAPK3'):
               continue
        if stmt.residue and stmt.position:
            site = '%s_%s%s' % (stmt.sub.name, stmt.residue, stmt.position)
            regulons[kinase].add(site)
    rows = []
    for kinase, sites in regulons.items():
        rows.append([kinase, 'Description'] + [s for s in sites])
    with open(filename, 'wt') as f:
        csvwriter = csv.writer(f, delimiter='\t')
        csvwriter.writerows(rows)

if __name__ == '__main__':
    reload = False
    if reload:
        phos_stmts = \
                get_phosphorylation_stmts('../work/gsea_sites.rnk')
        ac.dump_statements(phos_stmts, '../work/phospho_stmts.pkl')
    else:
        phos_stmts = ac.load_statements('../work/phospho_stmts.pkl')

    regulons_from_stmts(phos_stmts, '../work/kinase_regulons.gmt')

    #kinases = get_kinase_counts(phos_stmts)

    target_list = get_stmt_subject_object(phos_stmts, 'SUBJECT')

    # Get all Tubulin child nodes as the source list
    source_list = [('FPLX', 'Tubulin')]
    tubulin_ag = Agent('Tubulin', db_refs={'FPLX': 'Tubulin'})
    ex = Expander(bio_ontology)
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
