from indra.util import _require_python3
from random import shuffle


from indra.tools.reading.submit_reading_pipeline import \
    submit_reading, submit_combine, wait_for_complete

basen = 'kdm1a_round2'
pmids_file = 'RI106_RI103_pmid_upto20180608.txt'


def get_already_read():
    import boto3
    client = boto3.resource('s3')
    b = client.Bucket('bigmech')
    files = b.objects.filter(Prefix='reading_results/kdm1a_round2/reach/stmts')
    start_ixs = [int(f.key.split('/')[-1][:-4].split('_')[0]) for f in files.all()]
    not_read = set(list(range(0,166989,2000))) - set(start_ixs)
    for s in sorted(list(not_read)):
        print(s)


def combine_local_pickles():
    # I got the pickles as
    # /home/bmg16/.virtualenvs/py36/bin/aws s3 sync s3://bigmech/reading_results/kdm1a_round2/ .
    import glob
    import pickle
    pkls = glob.glob('/home/bmg16/data/kdm1a/reach/stmts/*.pkl')
    pkls += glob.glob('/home/bmg16/data/kdm1a/sparser/stmts/*.pkl')
    stmts = {}
    for pkl in pkls:
        with open(pkl, 'rb') as fh:
            print('Reading %s' % pkl)
            sts = pickle.load(fh)
            for pmid, ss in sts.items():
                if pmid in stmts:
                    stmts[pmid] += ss
                else:
                    stmts[pmid] = ss
    with open('kdm1a_round2.pkl', 'wb') as fh:
        pickle.dump(stmts, fh)
    return stmts


def process_pmids_file():
    with open(pmids_file, 'r') as fh:
        pmids = [l.strip() for l in fh.readlines()]
    return list(set(pmids))


if __name__ == '__main__':
    '''
    pmids = process_pmids_file()
    shuffle(pmids)
    '''
    to_read_pmids = '%s_pmids.txt' % basen
    '''
    with open(to_read_pmids, 'w') as fh:
        for pmid in pmids:
            fh.write('%s\n' % pmid)
    '''
    start_ixs = [100000,
    104000,
    108000,
    114000,
    120000,
    124000,
    128000,
    132000,
    134000,
    136000,
    142000,
    148000,
    156000,
    158000,
    164000
    ]
    for si in start_ixs:
        job_list = submit_reading(basen, to_read_pmids, ['reach', 'sparser'],
                                  start_ix=si, end_ix=si+2000, pmids_per_job=2000)
    #reading_res = wait_for_complete('run_reach_queue', job_list)
    #combine_res = submit_combine(basen, job_list)
