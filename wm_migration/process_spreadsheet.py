from indra.tools import assemble_corpus as ac
from indra.sources.eidos import migration_table_processor as mtp
from indra.preassembler.hierarchy_manager import YamlHierarchyManager
from indra.preassembler.make_eidos_hume_ontologies import load_yaml_from_url, \
    rdf_graph_from_yaml
from indra.belief.wm_scorer import get_eidos_scorer


if __name__ == '__main__':
    fname = 'grounded CAG links - New Ontology.xlsx'
    stmts = mtp.process_workbook(fname)
    hm = YamlHierarchyManager(load_yaml_from_url(wm_ont_url),
                              rdf_graph_from_yaml, True)
    stmts = ac.run_preassembly(stmts, return_toplevel=False,
                               belief_score=get_eidos_scorer(),
                               hierarchies={'entity': hm})
    stmts = ac.standardize_names_groundings(stmts)
