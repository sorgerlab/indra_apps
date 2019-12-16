import os
import pickle
from indra.tools.live_curation import Corpus
from indra.sources import eidos
from indra.preassembler.hierarchy_manager import YamlHierarchyManager
from indra.preassembler.make_wm_ontologies import load_yaml_from_url, \
    rdf_graph_from_yaml
import indra.tools.assemble_corpus as ac
from indra.statements import Influence, stmts_to_json_file
from indra.belief.wm_scorer import get_eidos_scorer
from indra.sources.eidos.reader import EidosReader
from process import reground_stmts, load_eidos, remove_namespaces, \
    remove_raw_grounding

onts = {
    'flattened_interventions':
        ('https://raw.githubusercontent.com/WorldModelers/Ontologies/master/'
         'wm_with_flattened_interventions_metadata.yml'),
    'main':
        ('https://raw.githubusercontent.com/WorldModelers/Ontologies/master/'
         'wm_metadata.yml'),
    'no_regrounding':
        ('https://raw.githubusercontent.com/WorldModelers/Ontologies/master/'
         'wm_metadata.yml'),
}

if __name__ == '__main__':
    eidos_reader = EidosReader()

    for key, ont_url in onts.items():
        with open('eidos_raw.pkl', 'rb') as fh:
            stmts = pickle.load(fh)
        #stmts = load_eidos()
        #stmts = ac.filter_by_type(stmts, Influence)
        #remove_namespaces(stmts, ['WHO', 'MITRE12', 'UN', 'PROPS',
        #                          'INTERVENTIONS'])
        ont_yml = load_yaml_from_url(ont_url)
        hm = YamlHierarchyManager(ont_yml, rdf_graph_from_yaml, True)
        hierarchies = {'entity': hm}
        if key != 'no_regrounding':
            stmts = reground_stmts(stmts, hm, 'WM', None, True)

        scorer = get_eidos_scorer()

        matches_fun, refinement_fun = None, None
        assembled_stmts = ac.run_preassembly(stmts,
                                             belief_scorer=scorer,
                                             matches_fun=matches_fun,
                                             refinement_fun=refinement_fun,
                                             normalize_equivalences=True,
                                             normalize_opposites=True,
                                             normalize_ns='WM',
                                             hierarchies=hierarchies,
                                             return_toplevel=False,
                                             poolsize=4)
        print('-----Finished assembly-----')
        remove_raw_grounding(assembled_stmts)
        corpus_name = 'eidos-regrounding-20191214-%s' % key
        fname = os.path.join('.', corpus_name + '.json')
        sj = stmts_to_json_file(assembled_stmts, fname, matches_fun=matches_fun)
        corpus = Corpus(assembled_stmts, raw_statements=stmts)
        corpus.s3_put(corpus_name)
