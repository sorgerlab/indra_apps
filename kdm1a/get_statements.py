import glob
import tqdm
import pickle
import logging
from indra.util import batch_iter
from indra.sources import indra_db_rest
from genewalk.get_indra_stmts import load_genes, load_indra_df, remap_go_ids


logger = logging.getLogger('get_statements')


def filter_to_genes(df, genes):
    """Filter a data frame of INDRA Statements given gene and FamPlex IDs."""
    # Look for sources that are in the gene list or whose families/complexes
    # are in the FamPlex term list
    ns_filter = (df.agA_ns == 'HGNC') & (df.agB_ns == 'HGNC')
    de_gene_filter = df.agA_id.isin(genes) | df.agB_id.isin(genes)
    df = df[ns_filter & de_gene_filter]
    logger.info('Filtered data frame to %d rows.' % len(df))
    return df


def download_statements(df, beliefs, ev_limit=1):
    """Download the INDRA Statements corresponding to entries in a data frame.
    """
    all_stmts = []
    unique_hashes = list(set(df.stmt_hash))
    batches = list(batch_iter(unique_hashes, 500))
    logger.info('Getting %d unique hashes from db' % len(unique_hashes))
    for group in tqdm.tqdm(batches):
        idbp = indra_db_rest.get_statements_by_hash(list(group),
                                                    ev_limit=ev_limit)
        all_stmts += idbp.statements
    for stmt in all_stmts:
        belief = beliefs.get(stmt.get_hash())
        if belief is None:
            logger.info('No belief found for %s' % str(stmt))
            continue
        stmt.belief = belief
    return all_stmts


if __name__ == '__main__':
    fnames = glob.glob('data/*20190919.csv')
    all_genes = set()
    for fname in fnames:
        all_genes |= set(load_genes(fname))
    logger.info('Loaded a total of %d unique genes' % len(all_genes))
    all_genes = sorted(list(all_genes))
    df = load_indra_df('/Users/ben/data/indra_db_sif_2021_01_26.pkl')
    df = filter_to_genes(df, all_genes)
    beliefs = {row.stmt_hash: row.belief for _, row in df.iterrows()}
    stmts = download_statements(df, beliefs)
    remap_go_ids(stmts)
    with open('output/indra_stmts_20191029_v2.pkl', 'wb') as fh:
        pickle.dump(stmts, fh)
