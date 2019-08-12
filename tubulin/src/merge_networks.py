import os
import re
import pickle
import argparse
import pandas as pd


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Merge multiple undirected'
                                     ' SIF networks into a single network by'
                                     ' taking the union of the edges')
    parser.add_argument('path', help='path to folder containing multiple'
                        ' networks')
    parser.add_argument('--pattern1',
                        default=r'^noisyEdges_[0-9]+$',
                        help='regex pattern that folders containing'
                        ' network files match')
    parser.add_argument('--pattern2',
                        default=r'^noisyEdges_[0-9]+_optimalForest.sif$',
                        help='regex pattern that network filenames'
                        ' match')
                        
    args = parser.parse_args()
    base = args.path
    pattern1 = args.pattern1
    pattern2 = args.pattern2
    edges = set()
    for folder in os.listdir(base):
        if re.search(args.pattern1, folder):
            for filename in os.listdir(os.path.join(base, folder)):
                if re.search(args.pattern2, filename):
                    edge_df = pd.read_csv(os.path.join(base, folder,
                                                       filename),
                                          sep='\t',
                                          names=['node1', 'pp', 'node2'],
                                          na_filter=False)
                    edges.update([tuple(sorted(edge)) for edge
                                  in edge_df[['node1', 'node2']].values])

    node1, node2 = zip(*edges)
    out = pd.DataFrame({'node1': node1, 'node2': node2})
    out.to_csv(os.path.join(base, 'merged_network.tsv'),
               sep='\t', header=False, index=False)
