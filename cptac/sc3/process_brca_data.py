import pickle
import numpy as np
from collections import Counter
from indra.util import read_unicode_csv
import scipy.stats


cell_lines = [
 'BT20',
 'HCC1806',
 'HS578T',
 'MCF10A',
 'MCF7',
 'MDAMB231',
 'PDX1258',
 'PDX1328',
 'SKBR3',
 'MDAMB134',
 'MDAMB157',
 'MDAMB361',
 'MDAMB436',
 'MDAMB453',
 'MDAMB468',
 'CAL51',
 'CAL851',
 'CAL120',
 'BT549',
 'HCC38',
 'HCC70',
 'HCC1395',
 'HCC1419',
 'HCC1500',
 'HCC1937',
 'HCC1954',
 'PDXHCI002',
 'CAMA1',
 'HCC1143',
 'HCC1428',
 'HME1',
 #'MCF10AREP2',
 'SUM1315',
 'SUM149',
 'SUM159',
 'T47D',
]


def get_cell_line_col_maps(pms_filename, ibaq_filename, rna_filename):
    pms_col_map = {}
    with open(pms_filename, 'rt') as f:
        pms_header = f.readline().strip().split(',')
        for col_ix, col in enumerate(pms_header):
            capcol = col.upper()
            if capcol in cell_lines:
                pms_col_map[capcol] = col_ix

    ibaq_col_map = {}
    with open(ibaq_filename, 'rt') as f:
        ibaq_header = f.readline().strip().split(',')
        for col_ix, col in enumerate(ibaq_header):
            capcol = col.upper()
            if capcol in cell_lines:
                ibaq_col_map[capcol] = col_ix

    rna_col_map = {}
    with open(rna_filename, 'rt') as f:
        rna_header = f.readline().strip().split('\t')
        for col_ix, col in enumerate(rna_header):
            capcol = col.upper()
            if capcol in cell_lines:
                rna_col_map[capcol] = col_ix

    return (pms_col_map, ibaq_col_map, rna_col_map)


def load_data(pms_filename, ibaq_filename, rna_filename):
    pms_col_map, ibaq_col_map, rna_col_map = \
            get_cell_line_col_maps(pms_filename, ibaq_filename, rna_filename)
    # Get the ibaq data first
    prot_labels = []
    prot_rows = []
    for row_ix, row in enumerate(read_unicode_csv(ibaq_filename, skiprows=1)):
        values = []
        gene_name = row[0]
        if gene_name == '0':
            gene_name = None
        uniprot_id = row[1]
        for cell_line in cell_lines:
            col_ix = ibaq_col_map[cell_line]
            if not row[col_ix]:
                val = np.nan
            else:
                val = float(row[col_ix])
            float(val)
            values.append(val)
        values = np.array(values)
        prot_labels.append((gene_name, uniprot_id))
        prot_rows.append(values)

    # Then get the phospho-MS data
    site_labels = []
    site_rows = []
    for row_ix, row in enumerate(read_unicode_csv(pms_filename, skiprows=1)):
        values = []
        site_name = row[0]
        uniprot_id = row[-3]
        site_position = row[-5]
        for cell_line in cell_lines:
            col_ix = pms_col_map[cell_line]
            if not row[col_ix]:
                val = np.nan
            else:
                val = float(row[col_ix])
            float(val)
            values.append(val)
        values = np.array(values)
        site_labels.append((site_name, uniprot_id, site_position))
        site_rows.append(values)

    # Then get the RNA data
    rna_labels = []
    rna_rows = []
    for row_ix, row in enumerate(read_unicode_csv(rna_filename, skiprows=1,
                                                  delimiter='\t')):
        values = []
        gene_name = row[0]
        for cell_line in cell_lines:
            col_ix = rna_col_map[cell_line]
            val = float(row[col_ix])
            values.append(val)
        values = np.array(values)
        rna_labels.append((gene_name,))
        rna_rows.append(values)

    prot_arr = np.array(prot_rows)
    site_arr = np.array(site_rows)
    rna_arr = np.array(rna_rows)

    return {'prot_labels': prot_labels, 'prot_arr': prot_arr,
            'site_labels': site_labels, 'site_arr': site_arr,
            'rna_labels': rna_labels, 'rna_arr': rna_arr}


def get_top_correlations(corrs, site_labels, pred_labels, max_corrs=100):
    site_dict = {}
    for row_ix in range(corrs.shape[0]):
        label = site_labels[row_ix]
        corr_row = corrs[row_ix,:]
        sort_ixs = np.argsort(np.abs(corr_row))
        corr_vec = [(pred_labels[ix], corr_row[ix])
                    for ix in sort_ixs[:-max_corrs:-1]]
        site_label = site_labels[row_ix]
        site_dict[site_label] = corr_vec
    return site_dict


def get_default_corrs(corr_dict, num_features=100):
    all_corrs = []
    # Add all the gene names
    for site, corr_list in corr_dict.items():
        all_corrs.extend([t[0][0] for t in corr_list if t[0][0]])

    ctr = Counter(all_corrs)
    ctr = sorted([(k, v) for k, v in ctr.items()], key=lambda x: x[1],
                 reverse=True)
    genes = [t[0] for t in ctr[0:num_features]]
    return genes


def build_prior():
    pass


if __name__ == '__main__':
    pms_filename = 'sources/Merged_dataset_normalized_subset.csv'
    ibaq_filename = 'sources/ibaq_normalized.csv'
    rna_filename = 'sources/RNAseq-rpkm.tsv'

    data = load_data(pms_filename, ibaq_filename, rna_filename)

    print("Calculating correlation coefficients")
    #scipy.stats.spearmanr(site_arr, prot_arr, nan_policy='omit')
    prot_corr_mat = scipy.stats.spearmanr(
                    np.vstack([data['site_arr'], data['prot_arr']]),
                    nan_policy='omit', axis=1)
    prot_corrs = prot_corr_mat[0][0:len(data['site_arr']),
                                  len(data['site_arr']):]
    rna_corr_mat = scipy.stats.spearmanr(
                    np.vstack([data['site_arr'], data['rna_arr']]),
                    nan_policy='omit', axis=1)
    rna_corrs = rna_corr_mat[0][0:len(data['site_arr']),
                                  len(data['site_arr']):]

    #with open('brca_data.pkl', 'wb') as f:
    #    pickle.dump(data, f)
    #np.save('brca_spearman', corr)

    prot_corr_dict = get_top_correlations(prot_corrs,
                                     data['site_labels'], data['prot_labels'])
    rna_corr_dict = get_top_correlations(rna_corrs,
                                     data['site_labels'], data['rna_labels'])

    prot_default = get_default_corrs(prot_corr_dict)
    rna_default = get_default_corrs(rna_corr_dict)

    prior = build_prior(prot_corr_dict, rna_corr_dict, prot_default,
                        rna_default)

"""
import sklearn
from sklearn.cross_decomposition import PLSRegression, CCA
from sklearn.preprocessing import Imputer

def vip(x, y, model):
    t = model.x_scores_
    w = model.x_weights_
    q = model.y_loadings_

    m, p = x.shape
    _, h = t.shape

    vips = np.zeros((p,))

    s = np.diag(t.T @ t @ q.T @ q).reshape(h, -1)
    total_s = np.sum(s)

    for i in range(p):
        weight = np.array([ (w[i,j] / np.linalg.norm(w[:,j]))**2
                            for j in range(h) ])
        vips[i] = np.sqrt(p*(s.T @ weight)/total_s)

    return vips


print("Running PLSR")
#plsr = PLSRegression(n_components=100)
plsr = CCA(n_components=36)
imp = Imputer()
prot_arr_nan = imp.fit_transform(prot_arr.T)
site_arr_nan = imp.fit_transform(site_arr.T)
plsr.fit(prot_arr_nan, site_arr_nan)

vips = vip(prot_arr_nan, site_arr_nan, plsr)

import sys
sys.exit()
"""

