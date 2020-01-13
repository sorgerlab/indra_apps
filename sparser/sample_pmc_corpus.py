import os
import pickle
import random
import indra
from indra.sources import sparser
from indra.literature import id_lookup
from indra.literature import pmc_client


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
                    with open('pmc_xmls/%s.nxml' % pmcid, 'w') as xfh:
                        xfh.write(xml)
                    done += 1
                    if done == k:
                        break


def read_sample(fname):
    stmts = {}
    with open(fname, 'r') as fh:
        pmcids = [l.strip() for l in fh.readlines()]
        for pmcid in pmcids:
            print('Reading %s' % pmcid)
            sp = sparser.process_nxml_file('pmc_xmls/%s.nxml' % pmcid,
                                           cleanup=False)
            if sp:
                stmts[pmcid] = sp.statements
            else:
                stmts[pmcid] = None
    return stmts


if __name__ == '__main__':
    pmids = get_pmids()
    get_sample(pmids, 500, 'pmcids_oa_xml_sample.txt')
    stmts = read_sample('pmcids_oa_xml_sample.txt')
    with open('pmcids_oa_xml_sample.pkl', 'wb') as fh:
        pickle.dump(fh, stmts)
