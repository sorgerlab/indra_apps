"""
Methods to poke around at INDRA statements and generate a sheet for 
comparing the flat and compositional grounders.
"""
import csv
from indra.statements import stmts_from_json_file

stmts = stmts_from_json_file('statements.json', format='jsonl')

def make_comparison_sheet(statements: list):
    header = ["id", "Evidence", "Subject Text", "Subject Groundings", "Object Text", "Object Groundings"]
    with open('wm_comparison_sheet.tsv', 'wt') as out_file:
        tsv_writer = csv.writer(out_file, delimiter='\t')
        tsv_writer.writerow(header)
        i = 1
        for statement in statements:
            belief = statement.belief
            evidences = statement.evidence
            for evidence in evidences:
                evidence_text = evidence.text
                subject_text = subj_from_evidence(evidence)
                object_text = obj_from_evidence(evidence)
                line = [i, evidence_text, subject_text, groundings_from_event(statement.subj), object_text, groundings_from_event(statement.obj)]
                tsv_writer.writerow(line)
                i += 1


def subj_from_evidence(evidence) -> str:
    """Returns text of subject for a single piece of evidence."""
    subject_text = evidence.annotations["agents"]["raw_text"][0]
    return subject_text


def obj_from_evidence(evidence) -> str:
    """Returns text of object for a single piece of evidence."""
    object_text = evidence.annotations["agents"]["raw_text"][1]
    return object_text


def get_entity_text(event):
    """Returns the text of the entity (subject or object)."""
    db_refs = event.to_json()["concept"]["db_refs"]
    entity_text = db_refs["TEXT"]
    return entity_text


def groundings_from_event(event):
    """Returns a list of (grounding, confidence) tuples from an event."""
    db_refs = event.to_json()["concept"]["db_refs"]
    groundings = db_refs["WM"]
    return groundings

make_comparison_sheet(stmts)