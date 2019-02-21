import json
from indra.sources.eidos.reader import EidosReader
from indra.sources import hume
from indra.statements import stmts_to_json_file

def load_config():
    with open('config.json', 'r') as fh:
        config = json.load(fh)
    return config


er = EidosReader()

def do_regrounding(stmts):
    concepts = []
    for stmt in stmts:
        for concept in stmt.agent_list():
            concept_txt = concept.db_refs.get('TEXT')
            concepts.append(concept_txt)
    groundings = er.reground_texts(concepts)
    # Update the corpus with new groundings
    idx = 0
    for stmt in stmts:
        for concept in stmt.agent_list():
            concept.db_refs['UN'] = groundings[idx]
            idx += 1
    return stmts


if __name__ == '__main__':
    config = load_config()
    fnames = config['files']
    for fname in fnames:
        print('Processing %s' % fname)
        hp = hume.process_jsonld_file(fname)
        parts = fname.split('/')
        new_fname = '%s_%s' % (parts[-2], parts[-1])
        new_fname = new_fname.replace('json-ld', 'json')
        print('Running regrounding')
        stmts = do_regrounding(hp.statements)
        print('Savig into JSON')
        stmts_to_json_file(hp.statements, new_fname)
