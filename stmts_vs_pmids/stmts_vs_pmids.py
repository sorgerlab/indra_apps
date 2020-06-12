import numpy as np
from matplotlib import pyplot as plt
from indra_db.query_db_stmts import *
from indra.util import plot_formatting as pf
from indra.tools import assemble_corpus as ac
from indra.belief import BeliefEngine
from indra.preassembler import Preassembler
from indra.ontology.bio import bio_ontology

# Get all the statements
stmts = get_statements()
#stmts = by_gene_role_type(stmt_type='Phosphorylation')
#with open('entrez_stmts.pkl', 'wb') as f:
#    pickle.dump(stmts, f)

#with open('entrez_stmts.pkl', 'rb') as f:
#    pickle.load(f)

# Get PMID dict
stmts_by_pmid = {}

for stmt in stmts:
    if len(stmt.evidence) > 1:
        print("WARNING: Statement has more than one piece of evidence.")
    pmid = stmt.evidence[0].pmid
    if pmid in stmts_by_pmid:
        stmts_by_pmid[pmid].append(stmt)
    else:
        stmts_by_pmid[pmid] = [stmt]

# Get all the statements
pmids = list(stmts_by_pmid.keys())
#num_trials = 3

sample_sizes_trials = [(10, 10), (30, 10), (100, 5), (300, 3),
                (1000, 3), (3000, 1), (10000, 1),
                (30000, 1), (100000, 1), (275000, 1)]
sample_sizes = [t[0] for t in sample_sizes_trials]

results = []
results_uniq = []
results_top = []
results_filt = []

for pmid_sample_size, num_trials in sample_sizes_trials:
    print("\n\nSample size: %d\n\n" % pmid_sample_size)
    trial_results = []
    trial_results_uniq = []
    trial_results_top = []
    trial_results_filt = []
    for i in range(num_trials):
        sample_pmids = np.random.choice(pmids, pmid_sample_size, replace=False)
        trial_stmts = [s for pmid in sample_pmids for s in stmts_by_pmid[pmid]]
        trial_results.append(len(trial_stmts))
        #
        be = BeliefEngine()
        pa = Preassembler(bio_ontology, trial_stmts)
        trial_stmts_top = pa.combine_related(poolsize=16, return_toplevel=True)
        trial_stmts_uniq = pa.unique_stmts
        trial_stmts_filt = ac.filter_belief(trial_stmts_top, 0.90)
        #trial_stmts_uniq = ac.run_preassembly_duplicate(pa, be)
        trial_results_uniq.append(len(trial_stmts_uniq))
        trial_results_top.append(len(trial_stmts_top))
        trial_results_filt.append(len(trial_stmts_filt))

    results.append((np.mean(trial_results), np.std(trial_results)))
    results_uniq.append((np.mean(trial_results_uniq), np.std(trial_results_uniq)))
    results_top.append((np.mean(trial_results_top), np.std(trial_results_top)))
    results_filt.append((np.mean(trial_results_filt), np.std(trial_results_filt)))

results = np.array(results)
results_uniq = np.array(results_uniq)
results_top = np.array(results_top)
results_filt = np.array(results_filt)

plt.ion()

plt.figure(figsize=(3, 3), dpi=150)
plt.plot(sample_sizes, results[:,0], label='Raw', marker='.')
plt.plot(sample_sizes, results_uniq[:,0], label='Unique', marker='.')
plt.plot(sample_sizes, results_top[:, 0], label='Top-level', marker='.')
plt.plot(sample_sizes, results_filt[:,0], label='P 0.9', marker='.')

#pf.set_fig_params()
ax = plt.gca()
ax.set_xscale('log')
ax.set_yscale('log')
pf.format_axis(ax, tick_padding=3, label_padding=3)
ax.set_xlabel('Number of Articles')
ax.set_ylabel('Number of Statements')
plt.legend(loc='lower right', frameon=False)
