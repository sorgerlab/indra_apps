#!/usr/bin/env python

import pandas as pd
import numpy as np
import networkx as nx


def p(x):
    """Process the Protein Id string in the df_24hr
    to the UniProtKB-AC id. It removes isoform information."""
    return x.split("|")[1].split('-')[0]


filename_tc  = "Mature_Neuron_MT_pMS_Stabilizer1_2_time_course_ys.xlsx"

df_tc = pd.read_excel("../input/" + filename_tc)

# Short aliases to help keep everything under 80 columns
EpoB0 = "DIV 14 EpoB 0 (stabilizer 1)"
EpoB60 = "DIV 14 EpoB 60 min (stabilizer 1)"
EpoB60FC = "EpoB 60 min FC"
EpoB60lFC = "EpoB60 abs(logFC)"

# Filter out everything with Max Score < 20
def safe_tofloat(x, default=0.0):
    """Convert a string to float if it is a valid floating point representation,
    otherwise set it to default. Needed for filtering out based on Max Score.
    Some Max Score values are not floating point numbers."""
    try:
        return float(x)
    except ValueError:
        return default

    
df_tc['Max Score'] = df_tc['Max Score'].apply(safe_tofloat)
df_tc = df_tc[df_tc['Max Score'] >= 20]

# Create a column for absolute log fold change
df_tc[EpoB60FC] = df_tc[EpoB60]/df_tc[EpoB0]
df_tc[EpoB60lFC] = df_tc[EpoB60FC].apply(lambda x: abs(np.log2(x)))

# File contains matching of UniprotKB-AC ID's and other identifiers. We use
# this because we do not trust the HGNC ID's in the original files. 
ident_df = pd.read_csv("../input/HUMAN_9606_idmapping.dat", sep="\t",
                       names=["UniProtKB-AC", "ID_type", "ID"], dtype=str)
uniprot_genename = ident_df[ident_df["ID_type"]=="Gene_Name"]
uniprot_genename = uniprot_genename[['UniProtKB-AC', 'ID']]


p = lambda x: x.split("|")[1].split('-')[0]
df_tc["UniProtKB-AC"] = df_tc["Protein Id"].apply(p)

df_tc = pd.merge(left=df_tc, right=uniprot_genename,
                 how="inner", on="UniProtKB-AC")

x = df_tc[df_tc['gene_symbol'] != df_tc['ID']]
# There were 91 genes with mismatch between UniProtKB-AC and gene_symbol


input_df = df_tc[["ID", "EpoB60 abs(logFC)"]]
input_df.columns = ["name", "prize"]
input_df = input_df.sort_values("prize", ascending=False)

# For genes with multiple isoforms and/or phosphosites,
# only keep row with max value of abs(logFC)
input_df = pd.DataFrame(input_df.groupby(["name"], sort=False)["prize"].max())
input_df.reset_index(level=0, inplace=True)


# Give UBC a negative prize. Otherwise it's too easy to end up with a
# bicycle spoke graph centered at UBC.
input_df.loc[input_df['name']=='UBC', 'prize'] = -10000

# Generate prize file
input_df.to_csv("../work/prize.txt", sep="\t", header=True, index=False)


# Generate a text file containing the list of measured genes. This can be used
# to highlight the measured genes in cytoscape
measured_genes = input_df['name']
measured_genes.to_csv('../work/measured_genes.txt', header=False, index=False)

