import copy
import pickle
import logging
import itertools
import pandas as pd
import ndex2.client
from goatools.obo_parser import GODag
from indra.util import batch_iter
from indra.statements import Complex
from indra.sources import indra_db_rest
import indra.tools.assemble_corpus as ac
from indra.databases import uniprot_client, ndex_client
from indra.assemblers.cx import NiceCxAssembler
from indra.preassembler import Preassembler
from indra.preassembler.hierarchy_manager import hierarchies
from indra.preassembler.custom_preassembly import agents_stmt_type_matches


logger = logging.getLogger('go_ndex')


go_dag = GODag('/Users/ben/genewalk/resources/go.obo')
goa_gaf = '/Users/ben/genewalk/resources/goa_human.gaf'


def _load_goa_gaf():
    """Load the gene/GO annotations as a pandas data frame."""
    goa_ec = {'EXP', 'IDA', 'IPI', 'IMP', 'IGI', 'IEP', 'HTP', 'HDA', 'HMP',
              'HGI', 'HEP', 'IBA', 'IBD'}
    goa = pd.read_csv(goa_gaf, sep='\t',
                      skiprows=23, dtype=str,
                      header=None,
                      names=['DB',
                             'DB_ID',
                             'DB_Symbol',
                             'Qualifier',
                             'GO_ID',
                             'DB_Reference',
                             'Evidence_Code',
                             'With_From',
                             'Aspect',
                             'DB_Object_Name',
                             'DB_Object_Synonym',
                             'DB_Object_Type',
                             'Taxon',
                             'Date',
                             'Assigned',
                             'Annotation_Extension',
                             'Gene_Product_Form_ID'])
    goa = goa.sort_values(by=['DB_ID', 'GO_ID'])
    # Filter out all "NOT" negative evidences
    goa['Qualifier'].fillna('', inplace=True)
    goa = goa[~goa['Qualifier'].str.startswith('NOT')]
    # Filter to rows with evidence code corresponding to experimental
    # evidence
    goa = goa[goa['Evidence_Code'].isin(goa_ec)]
    return goa


goa = _load_goa_gaf()


def load_indra_df(fname):
    """Return an INDRA Statement data frame from a pickle file."""
    logger.info('Loading INDRA DB dataframe')
    with open(fname, 'rb') as fh:
        df = pickle.load(fh)
    logger.info('Loaded %d rows from %s' % (len(df), fname))
    return df


def filter_to_genes(df, genes):
    """Filter a data frame of INDRA Statements given gene names."""
    source_filter = ((df.agA_ns == 'HGNC') & (df.agA_name.isin(genes)))
    target_filter = ((df.agB_ns == 'HGNC') & (df.agB_name.isin(genes)))
    df_filt = df[source_filter & target_filter]
    logger.info('Filtered data frame to %d rows.' % len(df_filt))
    return df_filt


def filter_out_medscan(stmts):
    new_stmts = []
    for stmt in stmts:
        new_evidence = [e for e in stmt.evidence if e.source_api != 'medscan']
        if not new_evidence:
            continue
        stmt.evidence = new_evidence
        new_stmts.append(stmt)
    return new_stmts


def download_statements(df):
    """Download the INDRA Statements corresponding to entries in a data frame.
    """
    all_stmts = []
    for idx, group in enumerate(batch_iter(df.hash, 500)):
        logger.info('Getting statement batch %d' % idx)
        stmts = indra_db_rest.get_statements_by_hash(list(group),
                                                     ev_limit=50)
        all_stmts += stmts
    return all_stmts


def expand_complex(stmt):
    """Replace a Complex statement with binary ones."""
    stmts = []
    added = set()
    for m1, m2 in itertools.combinations(stmt.members, 2):
        keys = (m1.entity_matches_key(), m2.entity_matches_key())
        if keys in added:
            continue
        if len(set(keys)) == 1:
            continue
        ordered = sorted([m1, m2], key=lambda x: x.entity_matches_key())
        c = Complex(ordered, evidence=copy.deepcopy(stmt.evidence))
        stmts.append(c)
        added.add(keys)
    return stmts


def assemble_statements(stmts, genes):
    """Run assembly on statements."""
    all_stmts = []
    for stmt in stmts:
        if isinstance(stmt, Complex):
            all_stmts += expand_complex(stmt)
        else:
            all_stmts.append(stmt)
    # This is to make sure that expanded complexes don't add nodes that
    # shouldn't be in the scope of the network
    all_stmts = ac.filter_gene_list(all_stmts, genes, policy='all')
    pa = Preassembler(hierarchies, stmts=all_stmts,
                      matches_fun=agents_stmt_type_matches)
    stmts = pa.combine_duplicates()
    return stmts


def get_genes_for_go_id(go_id):
    """Return genes that are annotated with a given go ID."""
    df = goa[goa['GO_ID'] == go_id]
    up_ids = sorted(list(set(df['DB_ID'])))
    gene_names = [uniprot_client.get_gene_name(up_id) for up_id in up_ids]
    gene_names = [g for g in gene_names if g]
    return gene_names


def get_cx_network(stmts, name, network_attributes):
    """Return NiceCxNetwork assembled from statements."""
    ca = NiceCxAssembler(stmts, name)
    ncx = ca.make_model(self_loops=False,
                        network_attributes=network_attributes)
    return ncx


def get_go_ids():
    """Get a list of all GO IDs."""
    go_ids = [k for k, v in go_dag.items() if not v.is_obsolete
              and v.namespace == 'biological_process']
    return go_ids


def format_and_upload_network(ncx, **ndex_args):
    ncx.apply_template(uuid=style_network_id, **ndex_args)
    network_url = ncx.upload_to(**ndex_args)
    network_id = network_url.split('/')[-1]
    nd = ndex2.client.Ndex2(**{(k if k != 'server' else 'host'): v
                               for k, v in ndex_args.items()})
    nd.make_network_public(network_id)
    nd.add_networks_to_networkset(network_set_id, [network_id])
    return network_id


if __name__ == '__main__':
    network_set_id = '4b7b1e45-b494-11e9-8bb4-0ac135e8bacf'
    style_network_id = '145a6a47-78ee-11e9-848d-0ac135e8bacf'
    username, password = ndex_client.get_default_ndex_cred(ndex_cred=None)
    ndex_args = {'server': 'http://public.ndexbio.org',
                 'username': username,
                 'password': password}
    indra_df = load_indra_df('/Users/ben/db.pkl')
    go_ids = get_go_ids()
    start = None
    started = False
    for go_id in go_ids:
        if not start or go_id == start:
            started = True
        if not started:
            continue
        logger.info('===============================')
        go_name = go_dag[go_id].name
        logger.info('Looking at %s (%s)' % (go_id, go_name))
        network_name = '%s (%s)' % (go_id, go_name)
        genes = get_genes_for_go_id(go_id)
        logger.info('%d genes for %s' % (len(genes), go_id))
        if len(genes) < 5 or len(genes) > 50:
            logger.info('Skipping: too few or too many genes.')
            continue
        df = filter_to_genes(indra_df, genes)
        if len(df) == 0:
            logger.info('Skipping: no statements found between genes.')
            continue
        stmts = download_statements(df)
        stmts = filter_out_medscan(stmts)
        stmts = assemble_statements(stmts, genes)
        network_attributes = {
            'networkType': 'pathway',
            'GO ID': go_id,
            'GO hierarchy': 'biological process',
            'Prov:wasGeneratedBy': 'INDRA',
            'Organism': 'Homo sapiens (Human)',
            'Description': go_dag[go_id].name,
            'Methods': 'This network was assembled automatically by INDRA ('
                       'http://indra.bio) by processing all available '
                       'biomedical literature with multiple machine reading '
                       'systems, and integrating curated pathway '
                       'databases. The network represents '
                       'mechanistic interactions between genes/proteins that '
                       'are associated with this GO process.',
        }
        ncx = get_cx_network(stmts, network_name, network_attributes)
        if not ncx.nodes:
            logger.info('Skipping: no nodes in network.')
            continue
        network_id = format_and_upload_network(ncx, **ndex_args)
        logger.info('Uploaded network with ID: %s' % network_id)
