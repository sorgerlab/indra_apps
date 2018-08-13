# coding: utf-8
get_ipython().run_line_magic('run', 'get_dark_kinase_stmts.py')
results.keys()
len(results)
stmts = [s for v in results.values() for s in v]
stmts
len(stmts)
len(results)
from indra.tools import assemble_corpus
ac = assemble_corpus
from indra.statements import *
phos = ac.filter_by_type(stmts, Phosphorylation)
len(phos)
dk_phos = [s for s in phos if s.enz is not None and s.enz.name in results]
dk_phos
len(dk_phos)
dk_phos_sites = [s for s in dk_phos if s.residue and s.position]
dk_phos_sites
len(dk_phos_sites)
frozenset
[frozenset([e for e in s.evidence]) for s in dk_phos_sites]
[frozenset([e.source_api for e in s.evidence]) for s in dk_phos_sites]
from collections import Counter
Counter([frozenset([e.source_api for e in s.evidence]) for s in dk_phos_sites])
85 + 57
dk_phos_sites
foo = ac.filter_genes_only(dk_phos_sites)
foo = ac.filter_human_only(foo)
foo
foo_sites = ['%s_%s%s' % (s.sub.name, s.residue, s.position) for s in foo]
foo_sites
set(foo_sites)
len(set(foo_sites))
import csv
with open('../tubulin/work/gsea_sites.rnk', 'rt') as f:
    csvreader = csv.reader(f, delimiter='\t')
    sites = []
    for site, val in csv_reader:
        sites.append(site)
        
with open('../tubulin/work/gsea_sites.rnk', 'rt') as f:
    csvreader = csv.reader(f, delimiter='\t')
    sites = []
    for site, val in csvreader:
        sites.append(site)
        
sites
set(sites)
len(set(sites))
foo_sites
set(foo_sites)
dark_sites = set(foo_sites).intersection(set(sites))
dark_sites
len(dark_sites)
