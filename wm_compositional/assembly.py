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
from indra_wm_service import Corpus
from indra.statements import stmts_to_json_file


reader_versions = {'flat':
                       {'cwms': '2020.08.28',
                        'hume': 'r2020_08_19_4',
                        'sofia': '1.1',
                        'eidos': '1.0.3'},
                   'compositional':
                       {'cwms': '2020.09.03',
                        'hume': 'r2020_09_28_4',
                        'sofia': '1.1',
                        'eidos': '1.0.4'}}


ont_url = 'https://github.com/WorldModelers/Ontologies/blob/'\
          '25690a258d02fdf1f35ce9140f7cd54145e2b30c/'\
          'CompositionalOntology_v2.1_metadata.yml'


def concept_matches_compositional(concept):
    wm = concept.db_refs.get('WM')
    if not wm:
        return concept.name
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


@register_pipeline
def print_grounding_stats(statements):
    logger.info('-----------------------------------------')
    logger.info('Number of Influences: %s' % len([s for s in statements if
                                                  isinstance(s, Influence)]))
    grs = []
    gr_combos = []
    evidences = 0
    evidence_by_reader = defaultdict(int)
    for stmt in statements:
        if isinstance(stmt, Influence):
            for concept in [stmt.subj.concept, stmt.obj.concept]:
                grs.append(concept.get_grounding())
            gr_combos.append((stmt.subj.concept.get_grounding(),
                              stmt.obj.concept.get_grounding()))
            evidences += len(stmt.evidence)
            for ev in stmt.evidence:
                evidence_by_reader[ev.source_api] += 1
    logger.info('Unique groundings: %d' % len(set(grs)))
    logger.info('Unique combinations: %d' % len(set(gr_combos)))
    logger.info('Number of evidences: %d' % evidences)
    logger.info('Number of evidences by reader: %s' %
                str(dict(evidence_by_reader)))
    logger.info('-----------------------------------------')
    return statements


if __name__ == '__main__':
    readers = ['sofia', 'eidos', 'hume', 'cwms']
    grounding = 'compositional'
    do_upload = False
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
                pp = eidos.process_json_file(fname, grounding_mode=grounding)
            elif reader == 'hume':
                pp = hume.process_jsonld_file(fname, grounding_mode=grounding)
            elif reader == 'cwms':
                pp = cwms.process_ekb_file(fname, grounding_mode=grounding)
            elif reader == 'sofia':
                pp = sofia.process_json_file(fname, grounding_mode=grounding)
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
        if grounding == 'compositional':
            validate_grounding_format(stmts)

    ap = AssemblyPipeline.from_json_file('assembly_%s.json' % grounding)
    assembled_stmts = ap.run(stmts)

    if do_upload:
        corpus_id = 'compositional_v4'
        stmts_to_json_file(assembled_stmts, '%s.json' % corpus_id)

        meta_data = {
            'corpus_id': corpus_id,
            'description': ('Assembly of 4 reader outputs with the '
                            'compositional ontology (%s).' % ont_url),
            'display_name': 'Compositional ontology assembly v3',
            'readers': readers,
            'assembly': {
                'level': 'grounding',
                'grounding_threshold': 0.6,
            },
            'num_statements': len(assembled_stmts),
            'num_documents': 382
        }
        corpus = Corpus(corpus_id, statements=assembled_stmts,
                        raw_statements=stmts,
                        meta_data=meta_data)
        corpus.s3_put()
