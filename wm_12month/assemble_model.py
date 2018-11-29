import os
import glob
import json
import indra.tools.assemble_corpus as ac
from indra.statements import stmts_to_json
from indra.sources import eidos, hume, cwms, sofia
from indra.belief.wm_scorer import get_eidos_scorer
from indra.preassembler.ontology_mapper import OntologyMapper, wm_ontomap


def process_eidos():
    fnames = glob.glob('docs/eidos/*.jsonld')
    stmts = []
    for fname in fnames:
        print(fname)
        ep = eidos.process_json_file(fname)
        for stmt in ep.statements:
            for ev in stmt.evidence:
                ev.annotations['provenance'][0]['document']['@id'] = \
                    os.path.basename(fname)
            stmts.append(stmt)
    return stmts


def process_hume():
    path = 'docs/hume/wm_m12.v8.full.v4.json-ld'
    hp = hume.process_jsonld_file(path)
    return hp.statements


def process_sofia():
    fname = 'docs/sofia/MITRE_AnnualEval_v1.xlsx'
    sp = sofia.process_table(fname)
    for stmt in sp.statements:
        for ev in stmt.evidence:
            prov = [{'document': {'@id': ev.pmid}}]
            ev.annotations['provenance'] = prov
    return sp.statements


def process_cwms():
    path = 'docs/cwms/20181114/*.ekb'
    ekbs = glob.glob(path)
    stmts = []
    for ekb in ekbs:
        cp = cwms.process_ekb_file(ekb)
        stmts += cp.statements
    for stmt in stmts:
        for ev in stmt.evidence:
            prov = [{'document': {'@id': ev.pmid}}]
            ev.annotations['provenance'] = prov
    return stmts


def assemble_stmts(stmts):
    om = OntologyMapper(stmts, wm_ontomap, scored=True, symmetric=False)
    om.map_statements()
    scorer = get_eidos_scorer()
    stmts = ac.run_preassembly(stmts, belief_scorer=scorer,
                               return_toplevel=False)
    return stmts


def dump_stmts_json(stmts, fname):
    jd = stmts_to_json(stmts, use_sbo=False)
    with open(fname, 'w') as fh:
        json.dump(jd, fh, indent=1)


if __name__ == '__main__':
    hume_stmts = process_hume()
    eidos_stmts = process_eidos()
    cwms_stmts = process_cwms()
    sofia_stmts = process_sofia()
    stmts = hume_stmts + eidos_stmts + cwms_stmts + sofia_stmts
    stmts = assemble_stmts(stmts)
    dump_stmts_json(stmts, 'wm_12_month_4_reader_20181128_v2.json')
