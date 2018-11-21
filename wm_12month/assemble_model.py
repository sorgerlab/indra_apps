import glob
from indra.sources import eidos, hume


def process_eidos():
    fnames = glob.glob('docs/eidos/*.jsonld')
    stmts = []
    for fname in fnames:
        print(fname)
        ep = eidos.process_json_file(fname)
        for stmt in ep.statements:
            for ev in stmt.evidence:
                ev.annotations['provenance'][0]['document']['@id'] = fname
            stmts.append(stmt)
    return stmts


def process_hume():
    path = 'docs/hume/expts/wm_m12.v6.full.v2/serialization/analytic/' + \
        'wm_m12.v6.full.v2.json-ld'
    hp = hume.process_jsonld_file(path)
    return hp.statements


if __name__ == '__main__':
    hume_stmts = process_hume()
    eidos_stmts = process_eidos()
