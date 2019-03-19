import copy
import math
import os
import re

colors_pastel = ["#e0f6e7", "#88aee1", "#eddaac", "#95bbef", "#daf4c5", "#cba9d3", "#b5d7a7", "#dec7f5", "#a1c293",
                 "#e8a7ba", "#72c8b8", "#e1a48e", "#7cd3eb", "#f1c1a6", "#99ceeb", "#c9aa8c", "#b8cff2", "#bbc49a",
                 "#b9b4dd", "#d7e0b5", "#9db3d6", "#c8f4d6", "#d59e9a", "#b7f3ed", "#eab2ae", "#8dd2d8", "#efc1d7",
                 "#98c3a6", "#edddf6", "#86bcb1", "#f6d4c9", "#a7dac9", "#bcadc4", "#d7e7cf", "#d8c8e0", "#cebe9b",
                 "#c7dfee", "#e0bfb4", "#a0c6d1", "#f2e9d6", "#afb9cb", "#c2d2ba", "#efd5dc", "#a6b79f", "#d2b9c0",
                 "#c6e1db", "#cab5a7", "#97b1ab", "#d5cdbb", "#abc5bf"]


def generate_brat_conf_files(input_dir: str = None):
    """
    Generate brat conf files based on an annotated set of documents

    Args:
        input_dir (str): input filepath

    Returns:
        None
    """

    regex_ann_filename = re.compile(r'.*\.ann')
    regex_entity = re.compile(r"T(\d+)\t([^\s]*)\s(\d+\s\d+;?)+\t([^\t]*)")
    regex_attribute = re.compile(r'^A(\d+)\t([^\s]+)\sT(\d+)\s(.*)')
    regex_relation = re.compile(r'^R(\d+)\t([^\s]+)\sArg1:T(\d+)\sArg2:T(\d+)')

    entities_list = set()
    attributes_list = {}
    relations_list = set()

    for root, dirs, files in os.walk(os.path.abspath(input_dir)):
        for filename in files:
            if regex_ann_filename.match(filename):
                with open(os.path.join(root, filename), "r", encoding="UTF-8") as input_file:
                    for line in input_file:

                        entity_match = regex_entity.match(line)
                        if entity_match:
                            entities_list.add(entity_match.group(2))

                        attrib_match = regex_attribute.match(line)
                        if attrib_match:
                            if attrib_match.group(2) not in attributes_list:
                                attributes_list[attrib_match.group(2)] = set(attrib_match.group(4))
                            else:
                                attributes_list[attrib_match.group(2)].add(attrib_match.group(4))

                        relation_match = regex_relation.match(line)
                        if relation_match:
                            relations_list.add(relation_match.group(2))

    write_confs(entities_list, attributes_list, relations_list, input_dir)


def get_last_ids(file_path: str = None):
    """
    Return last entity, relation, attribute and annotation IDs from a brat document

    Args:
        file_path (str): brat document filepath

    Returns:

    """

    regex_entity = re.compile(r'^T(\d+)\t([^\s]+)\s(.*)\t(.*)')
    regex_relation = re.compile(r'^R(\d+)\t([^\s]+)\sArg1:T(\d+)\sArg2:T(\d+)')
    regex_attribute = re.compile(r'^A(\d+)\t([^\s]+)\sT(\d+)\s(.*)')
    regex_annotation = re.compile(r'#(\d+)\tAnnotatorNotes\s(T|R)(\d+)\t(.*)')

    last_entity_id = 0
    last_att_id = 0
    last_relation_id = 0
    last_ann_id = 0

    with open(file_path, "r", encoding="UTF-8") as input_file:

        for line in input_file:

            entity_match = regex_entity.match(line)
            if entity_match:
                if int(entity_match.group(1)) > last_entity_id:
                    last_entity_id = int(entity_match.group(1))

            relation_match = regex_relation.match(line)
            if relation_match:
                if int(relation_match.group(1)) > last_relation_id:
                    last_relation_id = int(relation_match.group(1))

            attribute_match = regex_attribute.match(line)
            if attribute_match:
                if int(attribute_match.group(1)) > last_att_id:
                    last_att_id = int(attribute_match.group(1))

            annotation_match = regex_annotation.match(line)
            if annotation_match:
                if int(annotation_match.group(1)) > last_ann_id:
                    last_ann_id = int(annotation_match.group(1))

    return last_entity_id, last_att_id, last_relation_id, last_ann_id


def parse_ann_file(ann_filename: str = None):
    """
    Parse a brat annotation file and return a dictionary of entities and a list of relations.

    Args:
        ann_filename (str): brat document filepath

    Returns:
        (dict, dict): entities and relations
    """

    regex_entity = re.compile(r"^T(\d+)\t([^\s]+)\s([^\t]+)\t([^\t]*)$")
    regex_attribute = re.compile(r"^A(\d+)\t([^\s]+)\sT(\d+)\s(.*)$")
    regex_relation = re.compile(r"^R(\d+)\t([^\s]+)\sArg1:T(\d+)\sArg2:T(\d+)$")

    entities = dict()
    relations = dict()

    # Extraction entity annotations (without attributes)
    with open(ann_filename, "r", encoding="UTF-8") as input_file:
        for line in input_file:
            match_entity = regex_entity.match(line)
            if match_entity:

                brat_id = int(match_entity.group(1))

                current_entity = {
                    "id": brat_id,
                    "spans": list(),
                    "is_split": False,
                    "type": match_entity.group(2),
                    "text": match_entity.group(4).rstrip("\n"),
                    "attributes": dict()
                }

                spans = match_entity.group(3).split(";")
                for span in spans:
                    begin = int(span.split()[0])
                    end = int(span.split()[1])

                    current_entity["spans"].append((begin, end))

                if len(current_entity["spans"]) == 1:
                    current_entity["is_split"] = True

                entities[brat_id] = current_entity

    # Extracting entity attributes
    with open(ann_filename, "r", encoding="UTF-8") as input_file:
        for line in input_file:
            match_attribute = regex_attribute.match(line)
            if match_attribute:
                if int(match_attribute.group(3)) in entities:
                    entities[int(match_attribute.group(3))][
                        'attributes'][match_attribute.group(2)] = match_attribute.group(4)

    # Extracting relations
    with open(ann_filename, "r", encoding="UTF-8") as input_file:
        for line in input_file:
            match_relation = regex_relation.match(line)
            if match_relation:
                relations[int(match_relation.group(1))] = {
                    "type": match_relation.group(2),
                    "arg1": int(match_relation.group(3)),
                    "arg2": int(match_relation.group(4))
                }

    return entities, relations


def write_confs(entities_list: list = None,
                attributes_list: list = None,
                relations_list: list = None,
                input_dir: str = None):
    """
    Write brat configuration files to disk

    Args:
        entities_list (list): entity list
        attributes_list (list): attribute list
        relations_list (list): relation list
        input_dir (str): brat directory path

    Returns:
        None
    """

    with open(os.path.join(os.path.abspath(input_dir), "annotation.conf"), "w", encoding="UTF-8") as ann_conf:

        # Entities
        ann_conf.write("[entities]\n")
        for entity in entities_list:
            ann_conf.write("{0}\n".format(entity))

        # Relations
        ann_conf.write("[relations]\n")
        ann_conf.write("<OVERLAP> 	Arg1:<ANY>, Arg2:<ANY>, <OVL-TYPE>:<ANY>\n")
        for relation in relations_list:
            ann_conf.write("{0}\tArg1:<ANY>, Arg2:<ANY>\n".format(relation))

        # Events
        ann_conf.write("[events]\n")

        # Attributes
        ann_conf.write("[attributes]\n")
        for attribute in attributes_list:
            if attribute not in ["LEMMA", "FORM"]:
                ann_conf.write("{0}\tArg:<ANY>, Value:".format(attribute))
                for x, value in enumerate(attributes_list[attribute]):
                    if x < len(attributes_list[attribute])-1:
                        ann_conf.write(value+"|")
                    else:
                        ann_conf.write(value+"\n")

    with open(os.path.join(os.path.abspath(input_dir), "visual.conf"), "w", encoding="UTF-8") as visu_conf:
        visu_conf.write("[labels]\n")

        colors_entities = copy.deepcopy(colors_pastel)
        colors_relations = copy.deepcopy(colors_pastel)

        for entity in entities_list:
            visu_conf.write("{0} | {1}\n".format(entity, entity))

        for relation in relations_list:
            visu_conf.write("{0} | {1}\n".format(relation, relation))

        visu_conf.write("[drawing]\n")
        for idx, entity in enumerate(entities_list):

            bgcolor = colors_entities.pop(0)
            match_rgb = re.match("^#(..)(..)(..)$", bgcolor)

            rgb = [int(match_rgb.group(1), 16)/255, int(match_rgb.group(2), 16)/255, int(match_rgb.group(3), 16)/255]

            for i, item in enumerate(rgb):
                if item < 0.03928:
                    rgb[i] = item / 12.92
                else:
                    rgb[i] = math.pow((item + 0.055)/1.055, 2.4)

            lvl = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]

            if lvl > 0.179:
                fgcolor = "black"
            else:
                fgcolor = "white"

            visu_conf.write("{}\tfgColor:{}, bgColor:{}, borderColor:darken\n".format(
                entity,
                fgcolor,
                bgcolor
            ))

        for attribute in attributes_list:
            visu_conf.write("{0}\tposition:left, glyph:".format(attribute))
            for i in range(len(attributes_list[attribute])):
                if i < len(attributes_list[attribute])-1:
                    visu_conf.write("*|")
                else:
                    visu_conf.write("*\n")

        for relation in relations_list:
            visu_conf.write("{}\tcolor:{}, dashArray:3-3, arrowHead:triangle-5\n".format(
                relation,
                "#000000"
            ))
