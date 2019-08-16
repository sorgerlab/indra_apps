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


if __name__ == '__main__':
    df = pandas.read_csv('A375_Day4.csv')
    genes = list(df['HUGO'])
    hgnc_ids = get_hgnc_ids(genes)
    with open('A375_Day4_de_genes.txt', 'w') as fh:
        for hgnc_id in hgnc_ids:
            fh.write('HGNC:%s\n' % hgnc_id)