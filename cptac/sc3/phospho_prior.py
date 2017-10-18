from indra.tools import assemble_corpus as ac
import pickle
from collections import defaultdict
from indra.util import read_unicode_csv, write_unicode_csv
from matplotlib_venn import venn2, venn3
from matplotlib import pyplot as plt
from indra.databases import hgnc_client
from indra.statements import *
#from indra.db.query_db_stmts import by_gene_role_type
import synapseclient
from indra.databases import omnipath_client

def load_annotations_from_synapse(synapse_id='syn10998244'):
    syn = synapseclient.Synapse()
    syn.login()
    # Obtain a pointer and download the data
    syn_data = syn.get('syn10998244')

    prior = {}
    for row in read_unicode_csv(syn_data.path, delimiter='\t'):
        site_info = row[0]
        gene_list = row[1].split(',')
        prior[site_info] = gene_list
    return prior


def get_omnipath_stmts():
    stmts = omnipath_client.get_all_modifications()
    stmts = ac.filter_by_type(stmts, Phosphorylation)
    stmts = ac.map_sequence(stmts)
    stmts = ac.filter_human_only(stmts)
    stmts = ac.filter_genes_only(stmts)
    return stmts


def get_indra_db_stmts():
    stmts = by_gene_role_type(stmt_type='Phosphorylation')
    stmts = ac.map_grounding(stmts)
    # Expand families before site mapping
    stmts = ac.expand_families(stmts)
    stmts = ac.filter_grounded_only(stmts)
    stmts = ac.map_sequence(stmts)
    stmts = ac.run_preassembly(stmts, poolsize=4,
                               save='indra_phos_stmts_pre.pkl')
    stmts = ac.filter_human_only(stmts)
    stmts = ac.filter_genes_only(stmts)
    stmts = [s for s in stmts if s.enz and s.sub and s.residue and s.position]
    ac.dump_statements(stmts, 'indra_phos_stmts.pkl')
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


if __name__ == '__main__':
    omni_stmts = get_omnipath_stmts()
    import sys
    sys.exit()
    base_prior = load_annotations_from_synapse(synapse_id='syn10998244')

    phos_stmts = get_phosphosite_stmts()
    phos_prior = to_prior(phos_stmts)

    #indra_stmts = get_indra_db_stmts()
    indra_stmts = ac.load_statements('sources/indra_phos_stmts.pkl')
    indra_stmts = ac.filter_genes_only(indra_stmts)
    indra_prior = to_prior(indra_stmts)


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
        def get_ids(hgnc_name):
            hgnc_id = hgnc_client.get_hgnc_id(hgnc_name)
            up_id = hgnc_client.get_uniprot_id(hgnc_id)
            return {'HGNC': hgnc_id, 'UP': up_id}

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

