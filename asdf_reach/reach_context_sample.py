import json
import objectpath
from indra_db.util import unpack

#reach_output = db.select_sample_from_table(100, 'reading',
#        db.Reading.text_content_id == db.TextContent.id,
#        db.TextContent.text_type == 'fulltext', db.Reading.reader == 'REACH')

#reach_output = db.select_sample_from_table(1000, db.Reading)

def get_contexts(reach_output):
    event_contexts = []
    for reading in reach_output:
        if reading.reader != 'REACH':
            continue
        # Unzip and decode
        json_str = unpack(reading.bytes)
        json_str = json_str.replace('frame-id', 'frame_id')
        json_str = json_str.replace('argument-label', 'argument_label')
        json_str = json_str.replace('object-meta', 'object_meta')
        json_str = json_str.replace('doc-id', 'doc_id')
        json_str = json_str.replace('is-hypothesis', 'is_hypothesis')
        json_str = json_str.replace('is-negated', 'is_negated')
        json_str = json_str.replace('is-direct', 'is_direct')
        json_str = json_str.replace('found-by', 'found_by')
        try:
            json_dict = json.loads(json_str)
        except ValueError:
            logger.error('Could not decode JSON string.')
            return None
        tree = objectpath.Tree(json_dict)

        qstr = "$.events.frames"
        res = tree.execute(qstr)
        if res is None:
            continue
        for event_frame in res:
            try:
                context_id = event_frame['context']
                event_contexts.append((reading.id, context_id))
            except KeyError:
                continue
    return event_contexts
