import pandas
from indra.databases import hgnc_client


def get_hgnc_ids(gene_names):
    ids = []
    for gene in gene_names:
        if '.' in gene:
            print('%s is not an HGNC ID' % gene)
            continue
        hgnc_id = hgnc_client.get_current_hgnc_id(gene)
        if not hgnc_id:
            print('Invalid gene symbol: %s' % gene)
            continue
        ids.append(hgnc_id)
    return ids


def filter_df(df, log2_fc_thresh):
    df = df[df['log2FoldChange'].abs() > log2_fc_thresh]
    return df


if __name__ == '__main__':
    df = pandas.read_csv('A375_Day4.csv')
    print('Loaded data frame with %d rows' % len(df))
    df = filter_df(df, log2_fc_thresh=1)
    print('Filtered data frame to %d rows' % len(df))
    genes = list(df['HUGO'])
    hgnc_ids = get_hgnc_ids(genes)
    with open('A375_Day4_de_genes.txt', 'w') as fh:
        for hgnc_id in hgnc_ids:
            fh.write('HGNC:%s\n' % hgnc_id)
