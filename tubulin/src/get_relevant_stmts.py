import csv
from collections import defaultdict
from indra.db import client


sites = defaultdict(list)
with open('phosphosites.csv', 'rt') as f:
    csvreader = csv.reader(f, delimiter=',')
    for gene, site in csvreader:
        sites[gene].append(site)


