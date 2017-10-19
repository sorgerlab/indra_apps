from indra.util import read_unicode_csv, write_unicode_csv
from indra.databases import uniprot_client, hgnc_client
import subprocess

peptide_file = 'sources/retrospective_ova_phospho_sort_common_gene_10057.txt'

# Problem: statements from reading and many databases give results in terms
# of HGNC identifiers, which are mapped to canonical Uniprot IDs.
# However, protein data is mapped to RefSeq identifiers, which often refer
# to isoforms that don't match the canonical Uniprot sequence. Sometimes
# they also can't mapped to any of the isoforms of the canonical entry in Uniprot
# due to differences in sequence.
#
# Solution: Get RefSeq IDs for all peptides and group by gene symbol. Then
# Get a Uniprot ID corresponding to each RefSeq ID (ideally an isoform of the
# reviewed entry, though it doesn't really matter which one since the point is
# just to get the sequence for running an alignment.
# Get the Uniprot ID associated with the gene symbol.
#
# Get sequences for all Uniprot IDs associated with a given gene symbol.
# Run sequences through sequence alignment.
#
# Then, for a given peptide, look up phosphorylated site; get upid for refseq
# id. If matches canonical up_id from HGNC, go straight to sequence
# Otherwise, map to sequence
# alignment; get corresponding site on reference sequence; get priors associated
# with that site on canonical protein.


def load_refseq_seqs():
    seq_file = 'sources/GRCh38_latest_protein.faa'
    seq_data = {}
    with open(seq_file, 'rt') as f:
        cur_seq_lines = []
        for line in f:
            if line.startswith('>'):
                if cur_seq_lines:
                    fasta_header = cur_seq_lines[0].strip()
                    sequence = ''.join([l.strip() for l in cur_seq_lines[1:]])
                    seq_data[rs_id] = (fasta_header, sequence)
                    cur_seq_lines = []
                # Now, update the Refseq ID
                rs_id = line[1:line.index(' ')]
            cur_seq_lines.append(line)
    return seq_data


def load_refseq_up_map():
    map_file = 'sources/uniprot-refseq-prot.tab'
    id_map = {}
    for row in read_unicode_csv(map_file, delimiter='\t', skiprows=1):
        up_id = row[0]
        rs_id = row[1]
        if rs_id not in id_map:
            id_map[rs_id] = [up_id]
        else:
            id_map[rs_id].append(up_id)
    return id_map


if __name__ == '__main__':
    rs_data = load_refseq_seqs()

    invalid_gene_syms = set([])
    # Invalid refseq
    no_seq = set([])
    for row_ix, row in enumerate(
                    read_unicode_csv(peptide_file, delimiter='\t', skiprows=1)):
        if row_ix > 10:
            break
        site_id = row[0]
        print('%d: %s' % (row_ix, site_id))
        gene_sym, rem = site_id.split('.', maxsplit=1)
        refseq_id, site_info = rem.split(':')
        res = site_info[0].upper()
        pos = site_info[1:]
        try:
            pos = int(pos)
        except ValueError:
            print("\tSkipping double phosphosite %s" % site_id)
            continue
        seq_info = rs_data.get(refseq_id)
        if not seq_info:
            print("\tCouldn't get sequence for %s" % refseq_id)
            no_seq.add(refseq_id)
            continue
        fasta_header, sequence = seq_info
        if not sequence[pos-1] == res:
            print("\tInvalid site: %s" % site_id)
            continue

        # Next, get the main Uniprot sequence
        hgnc_id = hgnc_client.get_hgnc_id(gene_sym)
        if not hgnc_id:
            print("\tInvalid gene symbol %s" % gene_sym)
            invalid_gene_syms.add(gene_sym)
            continue
        up_id_main = hgnc_client.get_uniprot_id(hgnc_id)
        if not up_id_main or ', ' in up_id_main:
            print("\tCouldn't get canonical Uniprot ID from HGNC.")
            invalid_gene_syms.add(gene_sym)
            continue
        up_sequence = uniprot_client.get_sequence(up_id_main)

        # Check whether the sequences are identical!
        if sequence == up_sequence:
            print("\tSequences are identical, no need for sequence alignment!")
            continue

        in_file = 'aln/in/%s.fasta' % refseq_id
        out_file = 'aln/out/%s.fasta' % refseq_id
        with open(in_file, 'wt') as f:
            f.write('>%s\n' % up_id_main)
            f.write('%s\n' % up_sequence)
            f.write('%s\n' % fasta_header)
            f.write('%s\n' % sequence)

        print("\tRunning sequence alignment.")
        subprocess.call(['./clustal-omega-1.2.3-macosx', '-i', in_file,
                         '-o', out_file, '--force'])

        # Write the seq to a file
        #peptide_info = (site_id, gene_sym, refseq_id, up_id_from_rs, site_info)
        #ids.add(peptide_info)
    
    """
    id_map = load_refseq_up_map()

    # Invalid refseq
    ids = set([])
    invalid_rs = set([])
    gene_dict = {}
    for row in read_unicode_csv(peptide_file, delimiter='\t', skiprows=1):
        site_id = row[0]
        gene_sym, rem = site_id.split('.', maxsplit=1)
        refseq_id, site_info = rem.split(':')
        # Deal with the identifiers
        #hgnc_id = hgnc_client.get_hgnc_id(gene_sym)
        #if hgnc_id:
        #    up_id_from_hgnc = hgnc_client.get_uniprot_id(hgnc_id)
        up_id_from_rs = None
        try:
            up_id_from_rs = id_map[refseq_id][0]
        except KeyError:
            pass

        peptide_info = (site_id, gene_sym, refseq_id, up_id_from_rs, site_info)
        ids.add(peptide_info)

        if gene_sym not in gene_dict:
            hgnc_id = hgnc_client.get_hgnc_id(gene_sym)
            if not hgnc_id:
                invalid_gene_syms.add(gene_sym)
                continue
            up_id_main = hgnc_client.get_uniprot_id(hgnc_id)
            if not up_id_main or ', ' in up_id_main:
                invalid_gene_syms.add(gene_sym)
                continue
            gene_dict[gene_sym] = {'main': up_id_main,
                                   'refseq': set([up_id_from_rs])
        else:
            gene_dict[gene_sym]['refseq'].add(up_id_from_rs)

    # Now pick a gene and collect the UP IDs for getting sequences
    for gene in gene_dict.keys():
        up_main = gene_dict[gene]['main']
        refseq_up_ids = gene_dict[gene]['refseq']
        seq_id_list = []
        for refseq_up_id in refseq_up_ids:
            if refseq_up_id + '-1' == up_main:
                continue
            seq_id_list.append(refseq_up_id)
        if seq_id_list:
            seq_id_list.append(up_main)


    # Now collect, all uniprot IDs for each gene symbol, including the canonical
    # one


    write_unicode_csv('all_peptides_refseq.txt', ids)
    """

