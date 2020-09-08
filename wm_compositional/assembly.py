import os
import glob
import tqdm
from indra.sources import eidos, hume, cwms, sofia
from indra.statements import Influence, Event
from indra.tools import assemble_corpus as ac
from indra.ontology.world.ontology import WorldOntology
from indra_wm_service.assembly.dart import process_reader_outputs


flat_versions = {'cwms': '2020.08.28',
                 'hume': 'r2020_08_19_4',
                 'sofia': '1.1',
                 'eidos': '1.0.3'}

compositional_versions = {'cwms': '2020.09.03',
                          'hume': 'r2020_09_01',
                          'sofia': '1.1',
                          'eidos': '1.0.4'}


ont_url = 'https://github.com/WorldModelers/Ontologies/blob/'\
          '25690a258d02fdf1f35ce9140f7cd54145e2b30c/'\
          'CompositionalOntology_v2.1_metadata.yml'


def concept_matches_compositional(concept):
    wm = concept.db_refs.get('WM')
    if not wm:
        return None
    wm_top = tuple(entry[0] if entry else None for entry in wm[0])
    return wm_top


def matches_compositional(stmt):
    if isinstance(stmt, Influence):
        key = (stmt.__class__.__name__,
               concept_matches_compositional(stmt.subj.concept),
               concept_matches_compositional(stmt.obj.concept),
               stmt.polarity_count(),
               stmt.overall_polarity()
               )
    elif isinstance(stmt, Event):
        key = (stmt.__class__.__name__,
               concept_matches_compositional(stmt.concept),
               stmt.delta.polarity)
    return str(key)


def make_display_name(comp_grounding):
    entries = tuple(entry[0].split('/')[-1].replace('_', ' ')
                    if entry else None for entry in comp_grounding)
    entries_reversed = [entry for entry in entries[::-1] if entry is not None]
    return ' of '.join(entries_reversed)


if __name__ == '__main__':
    #fnames = glob.glob('/Users/ben/data/dart/eidos/1.0.4/*')
    fnames = glob.glob('/Users/ben/data/dart/hume/r2020_09_01/*')
    fnames = glob.glob('/Users/ben/data/dart/cwms/2020.09.03/*')
    stmts = []
    for fname in tqdm.tqdm(fnames):
        #ep = hume.process_jsonld_file(fname)
        ep = cwms.process_ekb_file(fname)
        doc_id = os.path.basename(fname)
        # TODO: fix document ID in provenance?
        for stmt in ep.statements:
            for ev in stmt.evidence:
                if 'provenance' not in ev.annotations:
                    ev.annotations['provenance'] = [
                        {'document': {'@id': doc_id}}]
                else:
                    prov = ev.annotations['provenance'][0]['document']
                    prov['@id'] = doc_id
        stmts += ep.statements

    stmts = ac.filter_by_type(stmts, Influence)
    assembled_stmts = \
        ac.run_preassembly(stmts, matches_fun=matches_compositional,
                           run_refinement=False)

    #ont = WorldOntology(ont_url)
    #ont.initialize()
