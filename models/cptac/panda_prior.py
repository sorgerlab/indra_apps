from indra.util import read_unicode_csv

class TargetInfo(object):
    def __init__(self, min_force, tf_list):
        self.min_force = min_force
        self.tf_list = tf_list

def main():
    filename = '../../../pypanda/TCGA_ovarian_output.txt'
    expr_dict = {}
    print("About to open")
    with open(filename, 'rt') as f:
        print("Opened")
        for ix, line in enumerate(f):
            row = line.strip().split('\t')
            if (ix+1) % 1000000 == 0:
                print((ix+1) / 1000000)
            tf = row[0]
            target = row[1]
            force = float(row[2])
            # Skip self edges
            if tf == target:
                continue
            if target not in expr_dict:
                expr_dict[target] = [(tf, force)]
            else:
                expr_dict[target].append((tf, force))

    # For each target, sort the 
    pruned = {}
    print("Iterating over genes")
    for ix, (target, edges) in enumerate(expr_dict.items()):
        if (ix+1) % 100 == 0:
            print(ix+1)
        sorted_edges = sorted(edges, key=lambda x: abs(x[1]), reverse=True)
        if len(sorted_edges) >= 100:
            end_ix = 100
        else:
            end_ix = len(sorted_edges)
        pruned[target] = sorted_edges[0:end_ix]
    return pruned


def save_prior(panda_dict):
    with open('expr_prior_ovarian_panda.tsv', 'wt') as f:
        for target in sorted(panda_dict.keys()):
            gene_str = ','.join([t[0] for t in panda_dict[target]])
            f.write('%s\t%s\n' % (target, gene_str))


if __name__ == '__main__':
    panda_dict = main()
    save_prior(panda_dict)
