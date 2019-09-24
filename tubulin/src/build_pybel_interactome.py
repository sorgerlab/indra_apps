#! /usr/bin/env python3
import csv
from collections import defaultdict
import networkx as nx
import pybel.constants as pc
from indra.assemblers import PybelAssembler
from indra.tools import assemble_corpus as ac
from indra.statements import *
from indra.statements import _aa_short_caps


def make_model(pbm):
    """PybelAssember's make_model throws an exception for some statements.
    i.e, missing residues, fractional positions
    . Reproduce here with error handling."""
    for stmt in pbm.statements:
        try:
            # Skip statements with no subject
            if stmt.agent_list()[0] is None and \
                    not isinstance(stmt, Conversion):
                continue
            # Assemble statements
            if isinstance(stmt, Modification):
                pbm._assemble_modification(stmt)
            elif isinstance(stmt, RegulateActivity):
                pbm._assemble_regulate_activity(stmt)
            elif isinstance(stmt, RegulateAmount):
                pbm._assemble_regulate_amount(stmt)
            elif isinstance(stmt, Gef):
                pbm._assemble_gef(stmt)
            elif isinstance(stmt, Gap):
                pbm._assemble_gap(stmt)
            elif isinstance(stmt, ActiveForm):
                pbm._assemble_active_form(stmt)
            elif isinstance(stmt, Complex):
                pbm._assemble_complex(stmt)
            elif isinstance(stmt, Conversion):
                pbm._assemble_conversion(stmt)
            elif isinstance(stmt, Autophosphorylation):
                pbm._assemble_autophosphorylation(stmt)
            elif isinstance(stmt, Transphosphorylation):
                pbm._assemble_transphosphorylation(stmt)
            else:
                logger.info('Unhandled statement: %s' % stmt)
        except Exception:
            pass
    return pbm.model


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


def dump_steiner_files(signed_graph, site_data,
                       prize_outpath, interactome_outpath):
    # Helper function to rewrite node names in an OmicsIntegrator-friendly way
    def _format_node(n):
        node_str = str(n)
        node_str = node_str.replace(' ', '_')
        node_str = node_str.replace("'", '')
        node_str = node_str.replace(',', '')
        return node_str
     
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
    with open(interactome_outpath, 'wt') as f:
        csvwriter = csv.writer(f, delimiter='\t')
        csvwriter.writerows(interactome_rows)
    with open(prize_outpath, 'wt') as f:
        csvwriter = csv.writer(f, delimiter='\t')
        csvwriter.writerows(prize_rows)

    return


if __name__ == "__main__":
    stmts = "../work/phospho_stmts.pkl"
    prize_outpath = "../work/pybel_prize.tsv"
    interactome_path = "../work/big_pybel_interactome2.tsv"
    site_file = "../work/gsea_sites.rnk"
    # Load the statements linking kinases/regulators to phospho sites
    # in the data
    stmts = ac.load_statements(stmts)

    # Employ filters to reduce network size
    stmts = ac.filter_grounded_only(stmts)
    stmts = ac.filter_human_only(stmts)
    stmts = ac.filter_genes_only(stmts)
    # In this data, statements of these two types will not act on
    # a short enough timescale to play a meaningful role
    stmts = ac.filter_by_type(stmts, DecreaseAmount, invert=True)
    stmts = ac.filter_by_type(stmts, IncreaseAmount, invert=True)
    stmts = ac.filter_by_type(stmts, Complex, invert=True)
    stmts = ac.filter_enzyme_kinase(stmts)
    
    # Assemble a pybel graph from statements
    pba = PybelAssembler(stmts)
    pb_graph = make_model(pba)

    signed_graph = to_signed_nodes(pb_graph)
    gn_dict = get_gene_node_dict(signed_graph)
    # Next we have to load the data file and assign values to

    site_data = read_site_file(site_file)

    dump_steiner_files(signed_graph, site_data,
                       prize_outpath, interactome_path)
