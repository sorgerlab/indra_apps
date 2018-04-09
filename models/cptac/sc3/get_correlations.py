import numpy as np
corr, pval = np.load('brca_spearman.np.npy')

with open('brca_spearman_labels.txt', 'rt') as f:
    data_labels = [line.strip() for line in f]

def get_top_correlations(corr, data_labels, max_corrs = 200, prot_only=True):
    site_dict = {}
    for row_ix in range(corr.shape[0]):
        label = data_labels[row_ix]
        if not '_' in label:
            continue
        corrs = corr[row_ix,:]
        sort_ixs = np.argsort(np.abs(corrs))
        corr_vec = []
        for sort_ix in sort_ixs[::-1]:
            if len(corr_vec) == max_corrs:
                break
            corr_label = data_labels[sort_ix]
            if '_' in corr_label:
                continue
            else:
                corr_val = corrs[sort_ix]
                corr_vec.append((corr_label, corr_val))
        site_dict[label] = corr_vec
    return site_dict

res = get_top_correlations(corr, data_labels)

all_corrs = []
for site, corr_list in res.items():
    all_corrs.extend([t[0] for t in corr_list])

from collections import Counter
ctr = Counter(all_corrs)
ctr = sorted([(k, v) for k, v in ctr.items()], key=lambda x: x[1], reverse=True)

genes = [t[0] for t in ctr[1:101]]

with open('brca_corr_prot_list.txt', 'wt') as f:
    for gene in genes:
        f.write('%s\n' % gene)

