import os
import time
import pickle
import random
import logging
import indra
from indra.sources import sparser
from indra.literature import id_lookup
from indra.literature import pmc_client


logger = logging.getLogger('sample_pmc_corpus')


def get_pmids():
    fname = os.path.join(indra.__path__[0], 'literature', 'pmids_oa_xml.txt')
    with open(fname, 'r') as fh:
        pmids = [l.strip() for l in fh.readlines()]
        pmids = [p for p in pmids if p]
    return pmids


def get_sample(pmids, k, fname):
    random.shuffle(pmids)
    done = 0
    with open(fname, 'w') as fh:
        for pmid in pmids:
            ids = id_lookup(pmid, 'pmid')
            pmcid = ids.get('pmcid')
            if pmcid:
                fh.write('%s\n' % pmcid)
                print('Downloading %s' % pmcid)
                xml = pmc_client.get_xml(pmcid)
                if xml:
                    with open('docs/pmc_xmls/%s.nxml' % pmcid, 'w') as xfh:
                        xfh.write(xml)
                    done += 1
                    if done == k:
                        break


def read_sample(fname):
    stmts = {}
    errors = {}
    with open(fname, 'r') as fh:
        pmcids = [l.strip() for l in fh.readlines()]
        ts = time.time()
        for pmcid in pmcids:
            print('Reading %s' % pmcid)
            sp = sparser.process_nxml_file('docs/pmc_xmls/%s.nxml' % pmcid,
                                           cleanup=False)
            if sp:
                stmts[pmcid] = sp.statements
                errors[pmcid] = sp.extraction_errors
            else:
                stmts[pmcid] = None
        te = time.time()
        logger.info('Took %.2f seconds' % (te-ts))
    return stmts, errors


if __name__ == '__main__':
    #pmids = get_pmids()
    #get_sample(pmids, 500, 'pmcids_oa_xml_sample.txt')
    stmts, errors = read_sample('pmcids_oa_xml_sample.txt')
    with open('pmcids_oa_xml_sample_v4.pkl', 'wb') as fh:
        pickle.dump([stmts, errors], fh)

