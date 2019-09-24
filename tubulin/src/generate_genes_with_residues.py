import pandas as pd

filename_tc  = "Mature_Neuron_MT_pMS_Stabilizer1_2_time_course_ys.xlsx"
df_tc = pd.read_excel("../input/" + filename_tc)

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

ident_df = pd.read_csv("../input/HUMAN_9606_idmapping.dat", sep="\t",
                       names=["UniProtKB-AC", "ID_type", "ID"], dtype=str)
uniprot_genename = ident_df[ident_df["ID_type"]=="Gene_Name"]
uniprot_genename = uniprot_genename[['UniProtKB-AC', 'ID']]


p = lambda x: x.split("|")[1].split('-')[0]
df_tc["UniProtKB-AC"] = df_tc["Protein Id"].apply(p)

df_tc = pd.merge(left=df_tc, right=uniprot_genename,
                 how="inner", on="UniProtKB-AC")

x = df_tc[df_tc['gene_symbol'] != df_tc['ID']]

output = df_tc[['gene_symbol', 'Site Position']]

output.to_csv("../work/genes_with_residues.csv", sep=",", index=False)
