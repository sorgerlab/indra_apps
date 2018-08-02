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
def safe_maxscore_cutoff(x, cutoff=20.0):
    """Convert get the max score for the peptide. In cases of multiple
    phosphorylation sites the string will be semicolon delimited; in this
    case split the string into multiple floats and use the maximum one as
    the max score."""
    if ';' in x:
        values = [float(v) for v in x.split(';')]
    else:
        values = [float(x)]
    return max(values) >= cutoff


def dump_site_prizes(df_tc):
    # Separate multiply phosphorylated from singly phosphorylated peptides
    site_df = df_tc[["ID", "Site Position", "EpoB60 abs(logFC)"]]

    # Some Pandas magic to split multiply phosphorylated sites into multiple
    # rows: see https://stackoverflow.com/questions/17116814/pandas-how-do-i-split-text-in-a-column-into-multiple-rows
    s = df_tc['Site Position'].str.split(';').apply(pd.Series, 1).stack()
    s.index = s.index.droplevel(-1)
    s.name = 'Site Position'
    del df_tc['Site Position']
    df_tc = df_tc.join(s)
    # Now take the max abs(fc) for any given site
    # Tip from https://stackoverflow.com/questions/15705630/python-getting-the-row-which-has-the-max-value-in-groups-using-groupby
    df_tc = df_tc.sort_values(EpoB60lFC, ascending=False).drop_duplicates(
                                             ['gene_symbol', 'Site Position'])
    site_df = df_tc[['ID', 'Site Position', 'EpoB60 abs(logFC)']]
    site_df.columns = ['name', 'site', 'abs_fc']
    site_df = site_df.sort_values('abs_fc', ascending=False)
    site_df.to_csv('../work/site_prizes.txt', sep='\t', header=True,
                   index=False)


if __name__ == '__main__':
    filename_tc  = "Mature_Neuron_MT_pMS_Stabilizer1_2_time_course_ys.xlsx"
    filename_24hr  = "Mature_Neuron_MT_pMS_destabilzer_stablizer_24hr_ys.xlsx"

    df_24hr = pd.read_excel("../input/" + filename_24hr)
    df_tc = pd.read_excel("../input/" + filename_tc,
                          dtype={'Site Position': str, 'Max Score': str})

    # Short aliases to help keep everything under 80 columns
    EpoB0 = "DIV 14 EpoB 0 (stabilizer 1)"
    EpoB60 = "DIV 14 EpoB 60 min (stabilizer 1)"
    EpoB60FC = "EpoB 60 min FC"
    EpoB60lFC = "EpoB60 abs(logFC)"

    # Filter the timecourse data to entries with Max Score > 20
    #df_tc['Max Score'] = df_tc['Max Score'].apply(safe_tofloat)
    df_tc = df_tc[df_tc['Max Score'].apply(
                    lambda x: safe_maxscore_cutoff(x, 20.0))]

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

    # Save the prizes for the individual sites
    dump_site_prizes(df_tc)

    # -----------
    input_df = df_tc[["ID", "EpoB60 abs(logFC)"]]
    input_df.columns = ["name", "prize"]
    input_df = input_df.sort_values("prize", ascending=False)

    # For genes with multiple isoforms and/or phosphosites,
    # only keep row with max value of abs(logFC)
    input_df = pd.DataFrame(input_df.groupby(["name"],
                            sort=False)["prize"].max())
    input_df.reset_index(level=0, inplace=True)

    # Give UBC a negative prize. Otherwise it's too easy to end up with a
    # bicycle spoke graph centered at UBC.
    input_df.loc[input_df['name']=='UBC', 'prize'] = -10000

    # Generate prize file
    input_df.to_csv("../work/prize.txt", sep="\t", header=True, index=False)


    # Generate a text file containing the list of measured genes. This can be
    # used to highlight the measured genes in cytoscape
    measured_genes = input_df['name']
    measured_genes.to_csv('../work/measured_genes.txt', header=False,
                          index=False)

