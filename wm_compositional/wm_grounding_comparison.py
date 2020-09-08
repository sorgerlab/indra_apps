"""
Methods to poke around at INDRA statements and generate a sheet for
comparing the flat and compositional grounders.
"""
import csv
from indra.statements import stmts_from_json_file
from tqdm import tqdm

# INDRA statements from flat ontology
STMTS_FLAT = stmts_from_json_file('statements.json', format='jsonl')

# does not exist yet!
#stmts_comp = stmts_from_json_file('statements_comp.json', format='jsonl')

def make_comparison_sheet(flat_statements, comp_statements):
    """Makes a tsv sheet to diff flat and compositional groundings."""
    header = ["Entity Text", "Grounding", "Confidence"]
    with open('wm_comparison_sheet.tsv', 'wt') as out_file:
        tsv_writer = csv.writer(out_file, delimiter='\t')
        tsv_writer.writerow(header)
        for statement in flat_statements[:500]:
            # get text/groundings for flat subject/object
            flat_subj_text = get_text(statement.subj)
            flat_subj_grounding = get_groundings(statement.subj)[0]
            flat_obj_text = get_text(statement.obj)
            flat_obj_grounding = get_groundings(statement.obj)[0]
            for statement2 in comp_statements[:500]:
                # get text/groundings for compositional subject/object
                # TODO: get into compositional tuples!
                comp_subj_text = get_text(statement2.subj)
                (comp_subj_groundings, comp_subj_scores) = (
                    get_compositional_groundings(statement2.subj))
                comp_obj_text = get_text(statement2.obj)
                (comp_obj_groundings, comp_obj_scores) = (
                    get_compositional_groundings(statement2.obj))

                if (flat_subj_text == comp_subj_text) & (flat_obj_text == comp_obj_text):
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


def get_text(event):
    """Returns the text of the entity (subject or object)."""
    entity_text = event.concept.db_refs["TEXT"]
    return entity_text


def get_groundings(event):
    """Returns a list of (grounding, confidence) tuples from an event."""
    groundings = event.concept.db_refs["WM"]
    return groundings


def get_compositional_groundings(event):
    """Returns a list of (grounding, confidence) tuples from an event.

    TODO: Check this! Since I don't have the compositional statements yet."""
    grounding = event.concept.db_refs["WM"][0]
    terms = []
    scores = []
    for item in grounding:
        if item is not None:
            term = item[0]
            score = item[1]
            terms.append(term)
            scores.append(score)
    return (terms, scores)


def get_cag_nodes(statements):
    """Returns number of nodes in CAG.

    Loops through list of statements, counts unique subject/object nodes. Does
    not distinguish if a node is the subject or object! Only counts it once.
    Uses the node TEXT to match, not just the subj/obj, since those can show
    the same Event but be unequal.
    """
    nodes = []
    for statement in tqdm(statements):
        subj = get_text(statement.subj)
        obj = get_text(statement.obj)
        if subj not in nodes:
            nodes.append(subj)
        if obj not in nodes:
            nodes.append(obj)
    print(f"{len(nodes)} unique nodes in the CAG.")
    return nodes


def get_self_loops(statements):
    """Gets list/number of nodes that point to themselves in the CAG.

    Finds nodes where the subject and object top GROUNDING is the same.
    """
    self_loops = []
    for statement in tqdm(statements):
        subj = statement.subj.concept.db_refs["WM"][0]
        obj = statement.obj.concept.db_refs["WM"][0]
        if subj == obj:
            self_loops.append(statement)
    print(f"{len(self_loops)} self-loops out of {len(statements)} statements.")
    return self_loops


def get_contradictions(statements):
    """Gets the list/number of contradictions in the CAG.

    Finds counts instances where the subj -> obj polarity for one node does
    not match the subj -> obj polarity for another node with the same edges.

    Adds raw statements to list, so even with the same text of subj/obj will
    probably be considered unique for counting purposes.

    TODO: Change list to include only text of statements, so we can reduce to
    unique contradictions?
    """
    contradictions = []
    i = 1
    total_comparisons = 0
    for statement in tqdm(statements):
        subject1 = get_text(statement.subj)
        object1 = get_text(statement.obj)
        subject_polarity = statement.subj.delta.polarity
        object_polarity = statement.obj.delta.polarity
        for j in range(i, len(statements)):
            subject2 = get_text(statements[j].subj)
            object2 = get_text(statements[j].obj)
            # only check for contradictions if the subj/obj match
            if (subject1 == subject2) and (object1 == object2):
                total_comparisons += 1
                subject2_polarity = statements[j].subj.delta.polarity
                object2_polarity = statements[j].obj.delta.polarity
                # check if their subj/obj polarities are equal
                subjects_equal = subject_polarity == subject2_polarity
                objects_equal = object_polarity == object2_polarity
                # if the polarity of the subjects are equal but not the
                # objects, or if the polarity of the objects are equal but
                # not the subjects, then we have a contradiction
                if (subjects_equal) and (not objects_equal):
                    contradiction = (statement, statements[j])
                    contradictions.append(contradiction)
                elif (not subjects_equal) and (objects_equal):
                #if not subjects_equal and objects_equal:
                    contradiction = (statement, statements[j])
                    contradictions.append(contradiction)
                # else condition is when polarities both match OR when both
                # polarities are the opposite
                # TODO: double check that this logic makes sense..
                else:
                    continue
        i += 1

    print(f"{len(contradictions):,} contradictions out of "
          f"{total_comparisons:,} comparisons "
          f"({(len(contradictions)/total_comparisons)*100} %).")
    return contradictions


def get_basic_stats(statements):
    """Returns a bunch of basic states from a list of statements."""
    print("Getting unique nodes in the CAG...")
    get_cag_nodes(statements)
    print("Getting self-loops in the CAG...")
    get_self_loops(statements)
    print("Getting contradictions in the CAG...")
    get_contradictions(statements)


get_basic_stats(STMTS_FLAT)
#make_comparison_sheet(STMTS_FLAT)
