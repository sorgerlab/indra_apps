from indra.util import _require_python3
from random import shuffle
from indra.literature import pubmed_client

from indra.tools.reading.submit_reading_pipeline import \
    submit_reading, submit_combine, wait_for_complete

basen = 'kdm1a'
pmids_file = 'pmid_KDM1A_upto20171205.txt'
genes_file = 'RI103_DEseq2_2h_hd_filterHI_HUGO.csv'

def process_genes_file():
    with open(genes_file, 'r') as fh:
        genes = [l.strip()[1:-1] for l in fh.readlines()]
    return genes

def process_pmids_file():
    with open(pmids_file, 'r') as fh:
        pmids = [l.strip() for l in fh.readlines()]
    return list(set(pmids))

def get_gene_pmids(genes):
    pmids = []
    for gene in genes:
        pmids_gene = pubmed_client.get_ids_for_gene(gene)
        print('%s: %d' % (gene, len(pmids_gene)))
        pmids += pmids_gene
    return list(set(pmids))


def run_reading(pmid_fname):
    job_list = submit_reading(basen, pmid_fname, ['reach'], pmids_per_job=2000)
    reading_res = wait_for_complete(job_list)
    combine_res = submit_combine(basen, job_list)

if __name__ == '__main__':
    #genes = process_genes_file()
    #pmids = get_gene_pmids(genes)
    #pmids += process_pmids_file()
    #pmids = list(set(pmids))
    #shuffle(pmids)
    to_read_pmids = '%s_pmids.txt' % basen
    #with open(to_read_pmids, 'w') as fh:
    #    for pmid in pmids:
    #        fh.write('%s\n' % pmid)
    run_reading(to_read_pmids)
