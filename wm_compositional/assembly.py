import os
import glob
import tqdm
from indra.sources import eidos, hume, cwms, sofia
from indra.statements import Influence, Event
from indra.tools import assemble_corpus as ac
from indra.ontology.world.ontology import WorldOntology
from indra.pipeline import register_pipeline, AssemblyPipeline
from indra_wm_service.assembly.operations import *
from indra_wm_service.assembly.dart import process_reader_outputs


reader_versions = {'flat':
                       {'cwms': '2020.08.28',
                        'hume': 'r2020_08_19_4',
                        'sofia': '1.1',
                        'eidos': '1.0.3'},
                   'compositional':
                       {'cwms': '2020.09.03',
                        'hume': 'r2020_09_01',
                        'sofia': '1.1',
                        'eidos': '1.0.4'}}


ont_url = 'https://github.com/WorldModelers/Ontologies/blob/'\
          '25690a258d02fdf1f35ce9140f7cd54145e2b30c/'\
          'CompositionalOntology_v2.1_metadata.yml'


@register_pipeline
def concept_matches_compositional(concept):
    wm = concept.db_refs.get('WM')
    if not wm:
        return concept.name
    wm_top = tuple(entry[0] if entry else None for entry in wm[0])
    return wm_top


@register_pipeline
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


if __name__ == '__main__':
    readers = ['eidos', 'sofia', 'hume', 'cwms']
    grounding = 'compositional'
    stmts = []
    for reader in readers:
        version = reader_versions[grounding][reader]
        pattern = '*' if reader != 'sofia' \
            else ('*_new' if grounding == 'compositional' else '*_old')
        fnames = glob.glob('/Users/ben/data/dart/%s/%s/%s' % (reader, version,
                                                              pattern))
        print('Found %d files for %s' % (len(fnames), reader))
        for fname in tqdm.tqdm(fnames):
            if reader == 'eidos':
                pp = eidos.process_json_file(fname)
            elif reader == 'hume':
                pp = hume.process_jsonld_file(fname)
            elif reader == 'cwms':
                pp = cwms.process_ekb_file(fname)
            elif reader == 'sofia':
                pp = sofia.process_json_file(fname)
            doc_id = os.path.basename(fname)[:32]
            for stmt in pp.statements:
                for ev in stmt.evidence:
                    if 'provenance' not in ev.annotations:
                        ev.annotations['provenance'] = [
                            {'document': {'@id': doc_id}}]
                    else:
                        prov = ev.annotations['provenance'][0]['document']
                        prov['@id'] = doc_id
            stmts += pp.statements

    ap = AssemblyPipeline.from_json_file('assembly_%s.json' % grounding)
    assembled_stmts = ap.run(stmts)
