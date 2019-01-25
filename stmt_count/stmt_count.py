import os
import time
import random
import pickle
from indra.util import read_unicode_csv
from indra_db.util import get_primary_db

def get_stmt_count_from_db():
    # Get all HGNC IDs
    hgnc_file = '../../indra/indra/resources/hgnc_entries.tsv'
    lines = read_unicode_csv(hgnc_file, delimiter='\t')
    # Skip the header line
    next(lines)
    hgnc_entries = [(line[1], line[0].split(':')[1])
                    for line in lines if line[3] == 'Approved']
    random.seed(1)
    random.shuffle(hgnc_entries)

    db = get_primary_db()
    CHECKPOINT_FILE = 'checkpoint.pkl'

    if os.path.exists(CHECKPOINT_FILE):
        print("Loading from checkpoint")
        with open(CHECKPOINT_FILE, 'rb') as f:
            start_ix, stmt_counts = pickle.load(f)
        if start_ix == len(hgnc_entries):
            return stmt_counts
    else:
        start_ix = 0
        stmt_counts = {}

    start = time.time()
    CHECKPOINT_INTERVAL = 100
    for ix in range(start_ix, len(hgnc_entries)):
        hgnc_name, hgnc_id = hgnc_entries[ix]
        # Save the state of the dict
        if ix != 0 and ix % CHECKPOINT_INTERVAL == 0:
            print("Saving checkpoint")
            with open(CHECKPOINT_FILE, 'wb') as f:
                pickle.dump((ix, stmt_counts), f)
        # Run the query
        q = db.filter_query(db.RawStatements,
                db.RawAgents.stmt_id == db.RawStatements.id,
                 db.RawAgents.db_name.like('HGNC'),
                 db.RawAgents.db_id.like(str(hgnc_id)))
        # Get the statement count
        stmt_count = q.count()
        # Print some stats
        elapsed = time.time() - start
        time_per_gene = elapsed / (ix - start_ix + 1)
        num_remaining = len(hgnc_entries) - (ix + 1)
        sec_remaining = time_per_gene * num_remaining
        min_remaining = sec_remaining / 60.
        print("%d of %d: %d statements for %s (%s): Est %.2f min remaining" %
                    (ix+1, len(hgnc_entries), stmt_count, hgnc_name, hgnc_id,
                     min_remaining))
        # Put count into dict
        stmt_counts[hgnc_name] = stmt_count
    # Save final results
    with open(CHECKPOINT_FILE, 'wb') as f:
        pickle.dump(len(hgnc_entries), stmt_counts)

    return stmt_counts



