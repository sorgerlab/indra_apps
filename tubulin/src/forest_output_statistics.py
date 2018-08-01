#!/usr/bin/env python3

import sys
import fileinput
import pandas as pd
import argparse

# Generate forest output statistics.
# Calculates the total number of prize and hidden nodes in the optimal forest,
# the average degrees of hidden and prize nodes, and the percentage of prize nodes
# that are included in the optimal forest


def get_stats(results_path):
    with open(results_path + "result_info.txt", 'r') as f:
        lines = f.readlines()

    stats = {}

    stats["total_prize_nodes"] = lines[15].split()[2]

    edge_attributes = pd.read_csv(results_path + "result_edgeattributes.tsv",
                                  sep="\t")
    node_attributes = pd.read_csv(results_path + "result_nodeattributes.tsv",
                                  sep="\t")

    node_attributes.TerminalType = node_attributes.TerminalType.apply(lambda x:
                                                                      "Prize" if
                                                                      x == "Proteomic"
                                                                      else "Hidden")

    edge_attributes["source"] = edge_attributes.Edge.apply(lambda x:
                                                          x.split(' ')[0])
    edge_attributes["target"] = edge_attributes.Edge.apply(lambda x:
                                                        x.split(' ')[2])
    def node_type(name):
        row = node_attributes.loc[node_attributes.Protein==name]
        return row.TerminalType.values[0]

    edge_attributes["source_type"] = edge_attributes.source.apply(node_type)
    edge_attributes["target_type"] = edge_attributes.target.apply(node_type)

    source_counts = edge_attributes.source_type.value_counts()
    target_counts = edge_attributes.target_type.value_counts()

    type_counts = node_attributes.TerminalType.value_counts()

    stats["prize_nodes_in_forest"] = type_counts.Prize
    stats["hidden_nodes_in_forest"]  = type_counts.Hidden

    prize_total_degree = source_counts.Prize + target_counts.Prize
    hidden_total_degree = source_counts.Hidden + target_counts.Hidden

    stats["avg_degree_prize"] = prize_total_degree/type_counts.Prize
    stats["average_degree_hidden"] = hidden_total_degree/type_counts.Hidden

    output = " ".join(["{} {}:".format(value, stat) for stat, value in
                       stats.items()])
    return output


if __name__ =="__main__":
    parser = argparse.ArgumentParser(description="Generate output statistics for forest")
    parser.add_argument("results_path")
    args = parser.parse_args()
    results_path = args.results_path
    sys.stdout.write(get_stats(results_path))




    

    

    

    
