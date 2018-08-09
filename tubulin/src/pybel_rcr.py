#! /usr/bin/env python3
import csv
import argparse
from collections import defaultdict
import networkx as nx
import pybel
import pybel.constants as pc
from indra.assemblers import PybelAssembler
from indra.tools import assemble_corpus as ac
from indra.statements import _aa_short_caps

def to_signed_nodes(pb_graph):
    new_edges = []
    for u, v, data in pb_graph.edges_iter(data=True):
        u_pos, u_neg, v_pos, v_neg = ((u, 0), (u, 1), (v, 0), (v, 1))
        if data[pc.RELATION] in pc.CAUSAL_INCREASE_RELATIONS:
            new_edges.extend([(u_pos, v_pos), (u_neg, v_neg)])
        elif data[pc.RELATION] in pc.CAUSAL_DECREASE_RELATIONS:
            new_edges.extend([(u_pos, v_neg), (u_neg, v_pos)])
    signed_graph = nx.DiGraph()
    signed_graph.add_edges_from(new_edges)
    return signed_graph

def get_gene_node_dict(graph):
    gn_dict = defaultdict(list)
    for node in graph.nodes():
        node_data, sign = node
        node_id = node_data[2]
        gn_dict[node_id].append(node)
    return gn_dict

def read_site_file(filename):
    site_data = defaultdict(list)
    with open(filename, 'rt') as f:
        csvreader = csv.reader(f, delimiter='\t')
        for gene_site, fold_change in csvreader:
            fc_float = float(fold_change)
            prize = abs(fc_float)
            sign = 1 if fc_float < 0 else 0
            gene, site = gene_site.split('_')
            residue = site[0]
            position = site[1:]
            site_data[gene].append((residue, position, prize, sign))
    return site_data

def dump_steiner_files(signed_graph, site_data):
    # Helper function to rewrite node names in an OmicsIntegrator-friendly way
    def _format_node(n):
        node_str = str(n)
        node_str = node_str.replace(' ', '_')
        node_str = node_str.replace("'", '')
        node_str = node_str.replace(',', '')
        return node_str
    """
    def _get_gene_site(n):
        if not (n[0] == pc.PROTEIN and len(n) > 3):
            return None
        # Iterate over sites
        for pmod in n[3:]:
            if pmod[0] == pc.PMOD and pmod[1][0] == pc.BEL_DEFAULT_NAMESPACE and\
               pmod[1][1] == 'Ph':
    """
    # Compile the interactome rows
    interactome_rows = []
    for u, v in signed_graph.edges_iter():
        row = [_format_node(u), _format_node(v), '0.99', 'D']
        interactome_rows.append(row)
    # Generate the prize file
    prize_rows = [['name', 'prize']]
    for gene, prizes in site_data.items():
        for prize_info in prizes:
            residue, position, prize, sign = prize_info
            aa_caps_res = _aa_short_caps(residue)
            prize_node = ((pc.PROTEIN, 'HGNC', gene,
                           (pc.PMOD, (pc.BEL_DEFAULT_NAMESPACE, 'Ph'),
                            aa_caps_res, position)), sign)
            prize_str = _format_node(prize_node)
            prize_rows.append([prize_str, prize])
    # Write files
    with open('pybel_interactome.tsv', 'wt') as f:
        csvwriter = csv.writer(f, delimiter='\t')
        csvwriter.writerows(interactome_rows)
    with open('pybel_prizes.tsv', 'wt') as f:
        csvwriter = csv.writer(f, delimiter='\t')
        csvwriter.writerows(prize_rows)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("stmts")
    parser.add_argument("--grounded", action="store_true")
    parser.add_argument("--human", action="store_true")
    parser.add_argument("--gene", action="store_true")
    
    args = parser.parse_args()
    stmts = args.stmts
    # Load the statements linking kinases/regulators to phospho sites in the data
    stmts = ac.load_statements(stmts)
    if grounded:
        stmts = ac.filter_grounded_only(stmts)
    if human:
        stmts = ac.filter_human_only(stmts)
    if gene:
        stmts = ac.filter_genes_only(stmts)
    

    # Assemble a PyBEL graph from the stmts
    pba = PybelAssembler(phos_stmts)
    pb_graph = pba.make_model()

    signed_graph = to_signed_nodes(pb_graph)
    gn_dict = get_gene_node_dict(signed_graph)
    # Next we have to load the data file and assign values to

    site_data = read_site_file('../work/gsea_sites.rnk')

    dump_steiner_files(signed_graph, site_data)
