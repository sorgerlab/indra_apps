"""
Methods to poke around at INDRA statements and generate a sheet for 
comparing the flat and compositional grounders.
"""
import csv
from indra.statements import stmts_from_json_file

# INDRA statements from flat ontology
stmts_flat = stmts_from_json_file('statements.json', format='jsonl')

# does not exist yet!
#stmts_comp = stmts_from_json_file('statements_comp.json', format='jsonl')

def make_comparison_sheet(flat_statements, comp_statements):
    header = ["Entity Text", "Grounding", "Confidence"]
    with open('wm_comparison_sheet.tsv', 'wt') as out_file:
        tsv_writer = csv.writer(out_file, delimiter='\t')
        tsv_writer.writerow(header)
        for statement in flat_statements[:500]:
            # get text/groundings for flat subject/object
            flat_subj_text = get_entity_text(statement.subj)
            flat_subj_grounding = get_groundings(statement.subj)[0]
            flat_obj_text = get_entity_text(statement.obj)
            flat_obj_grounding = get_groundings(statement.obj)[0]
            for statement in comp_statements[:500]:
                # get text/groundings for compositional subject/object
                # TODO: get into compositional tuples!
                comp_subj_text = get_entity_text(statement.subj)
                (comp_subj_groundings, comp_subj_scores) = get_compositional_groundings(statement.subj)
                comp_obj_text = get_entity_text(statement.obj)
                (comp_obj_groundings, comp_obj_scores) = get_compositional_groundings(statement.obj)

                if (flat_subj_text == comp_subj_text & flat_obj_text == comp_obj_text):
                    flat_subj_line = [flat_subj_text, flat_subj_grounding[0], flat_subj_grounding[1]]
                    comp_subj_line = [comp_subj_text, comp_subj_groundings, comp_subj_scores]
                    flat_obj_line = [flat_obj_text, flat_obj_grounding[0], flat_obj_grounding[1]]
                    comp_obj_line = [comp_obj_text, comp_obj_groundings, comp_obj_scores]
                    tsv_writer.writerow(flat_subj_line)
                    tsv_writer.writerow(comp_subj_line)
                    tsv_writer.writerow(flat_obj_line)
                    tsv_writer.writerow(comp_obj_line)


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


def get_groundings(event):
    """Returns a list of (grounding, confidence) tuples from an event."""
    db_refs = event.to_json()["concept"]["db_refs"]
    groundings = db_refs["WM"]
    return groundings


def get_compositional_groundings(event):
    """Returns a list of (grounding, confidence) tuples from an event."""
    db_refs = event.to_json()["concept"]["db_refs"]
    grounding = db_refs["WM"][0]
    terms = []
    scores = []
    for item in grounding:
        if item != None:
            term = item[0]
            score = item[1]
            terms.append(term)
            scores.append(score)
    return (terms, scores)


def get_CAG_nodes(statements):
    """Returns number of nodes in CAG.

    Loops through list of statements, counts unique subject/object nodes. Does
    not distinguish if a node is the subject or object! Only counts it once.
    Uses the node TEXT to match, not just the subj/obj, since those can show
    the same Event but be unequal.
    """
    nodes = []
    for statement in statements:
        subj = statement.subj.to_json()["concept"]["db_refs"]["TEXT"]
        obj = statement.obj.to_json()["concept"]["db_refs"]["TEXT"]
        if subj not in nodes:
            nodes.append(subj)
        if obj not in nodes:
            nodes.append(obj)
    print(len(nodes))
    return nodes


get_CAG_nodes(stmts_flat)
#make_comparison_sheet(stmts_flat)
