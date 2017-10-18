import numpy as np
from indra.tools import assemble_corpus as ac
from itertools import chain
import pickle
from collections import defaultdict
from indra.util import read_unicode_csv, write_unicode_csv
from matplotlib_venn import venn2, venn3
from matplotlib import pyplot as plt
from indra.databases import hgnc_client, uniprot_client
from indra.statements import *
from indra.db.query_db_stmts import by_gene_role_type
import synapseclient
from indra.databases import omnipath_client

def get_ids(hgnc_name):
    hgnc_id = hgnc_client.get_hgnc_id(hgnc_name)
    up_id = hgnc_client.get_uniprot_id(hgnc_id)
    return {'HGNC': hgnc_id, 'UP': up_id}


def load_ov_sites():
    ov_sites = set([])
    with open('sources/all_peptides.txt', 'rt') as f:
        for line in f:
            gene, site = line.strip().split(':')
            ov_sites.add((gene, site))
    return ov_sites


def load_annotations_from_synapse(synapse_id='syn10998244'):
    syn = synapseclient.Synapse()
    syn.login()
    # Obtain a pointer and download the data
    syn_data = syn.get('syn10998244')
    prior = {}
    stmts = []
    for row in read_unicode_csv(syn_data.path, delimiter='\t'):
        sub_name, site_info = row[0].split(':')
        res = site_info[0]
        pos = site_info[1:]
        gene_list = row[1].split(',')
        prior[site_info] = gene_list
        for enz_name in gene_list:
            enz = Agent(enz_name, db_refs=get_ids(enz_name))
            sub = Agent(sub_name, db_refs=get_ids(sub_name))
            stmt = Phosphorylation(enz, sub, res, pos)
            stmts.append(stmt)
    stmts = ac.map_sequence(stmts)
    stmts = ac.filter_human_only(stmts)
    #stmts = ac.filter_genes_only(stmts)
    return stmts


def get_omnipath_stmts():
    stmts = omnipath_client.get_all_modifications()
    phos_stmts = ac.filter_by_type(stmts, Phosphorylation)
    dephos_stmts = ac.filter_by_type(stmts, Dephosphorylation)
    stmts = phos_stmts + dephos_stmts
    stmts = ac.map_sequence(stmts)
    stmts = ac.filter_human_only(stmts)
    #stmts = ac.filter_genes_only(stmts)
    return stmts


def get_indra_phos_stmts():
    stmts = by_gene_role_type(stmt_type='Phosphorylation')
    stmts = ac.map_grounding(stmts)
    # Expand families before site mapping
    stmts = ac.expand_families(stmts)
    stmts = ac.filter_grounded_only(stmts)
    stmts = ac.map_sequence(stmts)
    stmts = ac.run_preassembly(stmts, poolsize=4,
                               save='sources/indra_phos_stmts_pre.pkl')
    stmts = ac.filter_human_only(stmts)
    stmts = ac.filter_genes_only(stmts)
    stmts = [s for s in stmts if s.enz and s.sub and s.residue and s.position]
    ac.dump_statements(stmts, 'sources/indra_phos_stmts.pkl')
    return stmts


def get_indra_reg_act_stmts():
    stmts = []
    for stmt_type in ('Activation', 'Inhibition', 'ActiveForm'):
        print("Getting %s statements from INDRA DB" % stmt_type)
        stmts += by_gene_role_type(stmt_type=stmt_type)
    stmts = ac.map_grounding(stmts, save='sources/indra_reg_act_gmap.pkl')
    stmts = ac.filter_grounded_only(stmts)
    stmts = ac.run_preassembly(stmts, poolsize=4,
                               save='sources/indra_reg_act_pre.pkl')
    stmts = ac.filter_human_only(stmts)
    stmts = ac.filter_genes_only(stmts)
    ac.dump_statements(stmts, 'sources/indra_reg_act_stmts.pkl')
    return stmts


def get_phosphosite_stmts():
    stmts = ac.load_statements('sources/phosphosite_stmts.pkl')
    stmts = ac.filter_human_only(stmts)
    stmts = ac.filter_genes_only(stmts)
    return stmts


def save_indra_db_stmts(stmts):
    csv_rows = [('KINASE', 'KINASE_TEXT', 'SUBSTRATE', 'SUBSTRATE_TEXT',
                 'RESIDUE', 'POSITION', 'SOURCE', 'DIRECT', 'PMID', 'SENTENCE')]
    for s in stmts:
        for e in s.evidence:
            is_direct = 'True' if e.epistemics.get('direct') else 'False'
            csv_rows.append((s.enz.name, s.enz.db_refs.get('TEXT'),
                             s.sub.name, s.sub.db_refs.get('TEXT'),
                             s.residue, s.position, e.source_api,
                             is_direct, e.pmid, e.text))
    write_unicode_csv('indra_phosphosites.csv', csv_rows)


def plot_overlap(indra_sites, ps_sites, nk_sites):
    print('INDRA: %d unique sites' % len(indra_sites))
    print('Phosphosite: %d unique sites' % len(phos_sites))
    print('Intersection: %d sites' % len(indra_sites.intersection(phos_sites)))
    print('Sites in INDRA (not Phosphosite): %d sites' %
            len(indra_sites.difference(phos_sites)))
    print('Sites in Phosphosite (not INDRA): %d sites' %
            len(phos_sites.difference(indra_sites)))

    indra_only = indra_sites.difference(phos_sites)

    plt.ion()
    plt.figure()
    venn3((indra_sites, phos_sites, nk_sites),
              set_labels=('REACH/INDRA', 'PhosphoSite', 'NetworKIN'))
    plt.savefig('kinase_substrate_overlap.pdf')


def to_prior(stmts):
    prior = {}
    for stmt in stmts:
        key = '%s:%s%s' % (stmt.sub.name, stmt.residue, stmt.position)
        if key not in prior:
            prior[key] = set([stmt.enz.name])
        else:
            prior[key].add(stmt.enz.name)
    return prior


def save_prior(prior):
    with open('phospho_prior_indra.tsv', 'wt') as f:
        for gene_key in sorted(prior.keys()):
            enzyme_list = ','.join(prior[gene_key])
            f.write('%s\t%s\n' % (gene_key, enzyme_list))


def get_stmt_sites(stmts):
    stmt_sites = set([])
    for stmt in stmts:
        site_info = '%s%s' % (stmt.residue, stmt.position)
        stmt_sites.add((stmt.sub.name, site_info))
    return stmt_sites


def coverage(set1, set2):
    coverage = len(set1.intersection(set2))
    return coverage


def load_brca_sites():
    filename = 'sources/Merged_dataset_normalized_subset.csv'
    sites = set([])
    for row in read_unicode_csv(filename, skiprows=1):
        entry_info = row[0]
        site_info = entry_info.split('_')[1]
        up_id = row[-1]
        gene_name = uniprot_client.get_gene_name(up_id)
        sites.add((gene_name, site_info))
    return sites


if __name__ == '__main__':
    indra_reg_stmts = get_indra_reg_act_stmts()
    import sys; sys.exit()
    """
    syn_stmts = load_annotations_from_synapse(synapse_id='syn10998244')
    omni_stmts = get_omnipath_stmts()
    phos_stmts = get_phosphosite_stmts()
    #indra_stmts = get_indra_db_stmts()
    indra_stmts = ac.load_statements('sources/indra_phos_stmts.pkl')
    indra_stmts = ac.filter_genes_only(indra_stmts)
    """

    with open('sources/stmt_cache.pkl', 'rb') as f:
        syn_stmts, omni_stmts, phos_stmts, indra_stmts = pickle.load(f)

    ov_sites = load_ov_sites()
    brca_sites = load_brca_sites()

    all_stmts = syn_stmts + omni_stmts + phos_stmts + indra_stmts

    print("Phosphosite: %d of %d peptides" %
          (coverage(ov_sites, get_stmt_sites(phos_stmts)), len(ov_sites)))
    print("Phosphosite + NetworKIN: %d of %d peptides" %
          (coverage(ov_sites, get_stmt_sites(syn_stmts)), len(ov_sites)))
    print("Omnipath (incl. PSP, Signor, et al.): %d of %d peptides" %
          (coverage(ov_sites, get_stmt_sites(omni_stmts)), len(ov_sites)))
    print("REACH/INDRA: %d of %d peptides" %
          (coverage(ov_sites, get_stmt_sites(indra_stmts)), len(ov_sites)))
    print("Combined prior: %d of %d peptides" %
          (coverage(ov_sites, get_stmt_sites(all_stmts)), len(ov_sites)))
    print("BRCA phospho-MS data: %d of %d peptides" %
          (coverage(ov_sites, brca_sites), len(ov_sites)))

    all_sites = get_stmt_sites(all_stmts).union(brca_sites)
    print("Combined all: %d of %d peptides" %
          (coverage(ov_sites, all_sites), len(ov_sites)))

    # Get activators of kinases

    # Mechanism link to find additional phosphorylation statements

    #indra_prior = to_prior(indra_stmts)
    db_stmts = syn_stmts + omni_stmts + phos_stmts
    db_prior = to_prior(db_stmts)
    db_counts = [len(kinases) for kinases in db_prior.values()]
    all_prior = to_prior(all_stmts)
    all_counts = [len(kinases) for kinases in all_prior.values()]
    plt.ion()
    plt.figure()
    plt.hist(np.log10(db_counts), bins=20, alpha=0.5)
    plt.hist(np.log10(all_counts), bins=20, alpha=0.5)



    #save_prior(all_stmts)

    # FOR PLOTTING OVERLAP
    #def get_kin_sub(stmts):
    #    return set([(s.enz.name, s.sub.name, s.position) for s in stmts])
    #indra_sites = get_kin_sub(indra_stmts)
    #phos_sites = get_kin_sub(phos_stmts)
    #nk_sites = get_kin_sub(nk_stmts)


"""
# NOTE: not used anymore because data is being loaded from Synapse
def get_ovarian_nk_stmts():
    stmts = []
    for row_ix, row in enumerate(
                        read_unicode_csv('ovarian_kinase_substrate_table.csv',
                                         skiprows=1)):

        source = row[5]
        sources = set()
        if source != 'NetworKIN':
            sources.add(source)
            continue
        site_info = row[0]
        residue = site_info[0].upper()
        position = site_info[1:]
        enz_hgnc_name = row[2].upper()
        sub_hgnc_name = row[4].upper()
        ev = Evidence(source_api='networkin', source_id='row_%d' % (row_ix+2))
        enz = Agent(enz_hgnc_name, db_refs=get_ids(enz_hgnc_name))
        sub = Agent(sub_hgnc_name, db_refs=get_ids(sub_hgnc_name))
        stmt = Phosphorylation(enz, sub, residue, position, evidence=ev)
        stmts.append(stmt)
    print("Non NK sources: %s" % sources)
    stmts = ac.filter_human_only(stmts)
    stmts = ac.filter_genes_only(stmts)
    return stmts
"""

"""
def get_ovarian_sites():
    ov_sites = []
    for row in read_unicode_csv('ovarian_phosphopeptides.csv',
                                skiprows=1):
        substrate = row[0]
        position = row[2][1:]
        ov_sites.append((substrate, position))
    ov_sites = set(ov_sites)
    return ov_sites
"""

