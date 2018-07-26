import copy
import math
import os
import re
import shutil

from .utils import remove_abs, ensure_dir, get_other_extension

colors_pastel = ["#e0f6e7", "#88aee1", "#eddaac", "#95bbef", "#daf4c5", "#cba9d3", "#b5d7a7", "#dec7f5", "#a1c293",
                 "#e8a7ba", "#72c8b8", "#e1a48e", "#7cd3eb", "#f1c1a6", "#99ceeb", "#c9aa8c", "#b8cff2", "#bbc49a",
                 "#b9b4dd", "#d7e0b5", "#9db3d6", "#c8f4d6", "#d59e9a", "#b7f3ed", "#eab2ae", "#8dd2d8", "#efc1d7",
                 "#98c3a6", "#edddf6", "#86bcb1", "#f6d4c9", "#a7dac9", "#bcadc4", "#d7e7cf", "#d8c8e0", "#cebe9b",
                 "#c7dfee", "#e0bfb4", "#a0c6d1", "#f2e9d6", "#afb9cb", "#c2d2ba", "#efd5dc", "#a6b79f", "#d2b9c0",
                 "#c6e1db", "#cab5a7", "#97b1ab", "#d5cdbb", "#abc5bf"]

colors_fancy = ["#9bd1c6", "#e6ade5", "#d8f3af", "#74aff3", "#fae09f", "#c9b5f7", "#bcd794", "#adb5f0", "#a1bb7a",
                "#e2c2f3", "#8ac793", "#eda4c1", "#81e6d3", "#eea899", "#41c9dc", "#efb98d", "#67c6f2", "#f4f5b6",
                "#8eb4e8", "#dedfa2", "#a3c9fe", "#adaf74", "#bda7d4", "#a7eabe", "#e4bad9", "#d8fbc9", "#c7c2ec",
                "#c2c387", "#7cd3eb", "#dbc58e", "#8beaf7", "#e3aba7", "#84eced", "#ebb9c7", "#64c8c5", "#dfb89b",
                "#acd2f2", "#a7c99a", "#97b8d8", "#c3e5b5", "#8dd2d8", "#c0b18d", "#c3f4df", "#d5c5a1", "#80b6aa",
                "#eadab6", "#88c6a5", "#dee7bc", "#a5d1b3", "#bbc49a"]

colors_intense = ["#d040bb", "#52c539", "#bb46e0", "#8bba3c", "#5533c0", "#54be66", "#6c63da", "#b4b43b", "#742d90",
                  "#42822b", "#e14498", "#4ecc99", "#e1435b", "#399b71", "#e75a30", "#808ae6", "#daae40", "#3f2f6a",
                  "#e28b2f", "#4a62a8", "#b8351f", "#58c3b7", "#8c2425", "#59b6cf", "#b0385e", "#8fbf8f", "#d17bd7",
                  "#737d28", "#912f6f", "#729563", "#9769ab", "#a4802b", "#69a6e0", "#a55e27", "#446c90", "#dd986a",
                  "#368686", "#76341a", "#b79ed0", "#2f481b", "#d97fa1", "#37694a", "#6b263d", "#b8b274", "#724c6f",
                  "#6b5121", "#d2968e", "#5f3629", "#82764b", "#b7645a"]


def parse_ann_file(ann_filename):
    """
    Parse a brat .ann file and return a dictionary of entities and a list of relations.
    :param ann_filename: brat .ann file to parse
    :return: entities (dict), relations (list)
    """

    regex_entity = re.compile('^T(\d+)\t([^\s]+)\s([^\t]+)\t([^\t]*)$')
    regex_attribute = re.compile('^A(\d+)\t([^\s]+)\sT(\d+)\s(.*)$')
    regex_relation = re.compile('^R(\d+)\t([^\s]+)\sArg1:T(\d+)\sArg2:T(\d+)$')

    entities = list()
    relations = list()
    entity_index = list()

    # Extraction entity spans and types
    with open(ann_filename, "r", encoding="UTF-8") as input_file:
        for line in input_file:
            match_entity = regex_entity.match(line)
            if match_entity:
                current_entity = {
                    'span': list(),
                    'type': match_entity.group(2),
                    'brat_id': int(match_entity.group(1)),
                    'text': match_entity.group(4).rstrip("\n"),
                    'attributes': list()
                }

                spans = match_entity.group(3).split(";")
                for span in spans:
                    begin = int(span.split()[0])
                    end = int(span.split()[1])

                    current_entity["span"].append((begin, end))

                entities.append(current_entity)
                entity_index.append(current_entity["brat_id"])

    # Extracting entity attributes
    with open(ann_filename, "r", encoding="UTF-8") as input_file:
        for line in input_file:
            match_attribute = regex_attribute.match(line)
            if match_attribute:
                if int(match_attribute.group(3)) in entity_index:
                    entities[entity_index.index(int(match_attribute.group(3)))]['attributes'].append({
                        "label": match_attribute.group(2),
                        "value": match_attribute.group(4)
                    })

    # Extracting relations
    with open(ann_filename, "r", encoding="UTF-8") as input_file:
        for line in input_file:
            match_relation = regex_relation.match(line)
            if match_relation:
                relations.append({
                    "brat_id": int(match_relation.group(1)),
                    "type": match_relation.group(2),
                    "arg1": int(match_relation.group(3)),
                    "arg2": int(match_relation.group(4))
                })

    return entities, relations


def generate_brat_conf_files(input_dir):

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


def write_confs(entities_list, attributes_list, relations_list, input_dir, convert_names=False):

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

        colors_entities = copy.deepcopy(colors_intense)
        colors_relations = copy.deepcopy(colors_intense)

        for entity in entities_list:
            if convert_names:
                visu_conf.write("{0} | {1}\n".format(entity, _decode_string(entity)))
            else:
                visu_conf.write("{0} | {1}\n".format(entity, entity))

        for relation in relations_list:
            if convert_names:
                visu_conf.write("{0} | {1}\n".format(relation, _decode_string(relation)))
            else:
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

            l = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]

            if l > 0.179:
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
                colors_relations.pop()
            ))


def _decode_string(string):

    converted_string = ""
    current = 0

    for match in re.finditer('--(\d+)--', string):

        begin = match.start()

        for i, char in enumerate(string[current:begin]):
            converted_string += char

        converted_string += chr(int(match.group(1)))
        current = match.end()

    if current != len(string):
        converted_string += string[current:]

    return converted_string


def get_last_ids(file_path):

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


def parse_ann_file_v2(ann_filename):
    """
    Parse a brat .ann file and return a dictionary of entities and a list of relations.
    :param ann_filename: brat .ann file to parse
    :return: entities (dict), relations (list)
    """

    regex_entity = re.compile("^T(\d+)\t([^\s]+)\s([^\t]+)\t([^\t]*)$")
    regex_attribute = re.compile("^A(\d+)\t([^\s]+)\sT(\d+)\s(.*)$")
    regex_relation = re.compile("^R(\d+)\t([^\s]+)\sArg1:T(\d+)\sArg2:T(\d+)$")

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


def merge_sets(first_set_path, second_set_path, output_path):

    for root, dirs, files in os.walk(os.path.abspath(first_set_path)):
        for filename in files:
            if re.match("^.*\.ann$", filename):

                subdir = remove_abs(re.sub(re.escape(os.path.abspath(first_set_path)), "", root))

                source_ann_first = os.path.join(root, filename)
                source_ann_second = os.path.join(os.path.abspath(second_set_path), subdir, filename)

                source_txt = os.path.join(root, get_other_extension(filename, "txt"))

                target_dir = os.path.join(os.path.abspath(output_path), subdir)
                target_ann = os.path.join(target_dir, filename)
                target_txt = os.path.join(target_dir, get_other_extension(filename, "txt"))

                ensure_dir(target_dir)
                shutil.copy(source_txt, target_txt)

                first_entities, first_relations = parse_ann_file_v2(source_ann_first)
                second_entities, second_relations = parse_ann_file_v2(source_ann_second)

                entity_id = 1
                relation_id = 1

                target_entities = dict()
                target_relations = dict()

                mapping = dict()

                for brat_id, entity in first_entities.items():
                    mapping[brat_id] = entity_id
                    target_entities[entity_id] = entity
                    target_entities[entity_id]["brat_id"] = entity_id

                    entity_id += 1

                for brat_id, relation in first_relations.items():
                    target_relations[relation_id] = relation
                    target_relations[relation_id]["arg1"] = mapping[relation["arg1"]]
                    target_relations[relation_id]["arg2"] = mapping[relation["arg2"]]

                    relation_id += 1

                mapping = dict()

                for brat_id, entity in second_entities.items():
                    mapping[brat_id] = entity_id
                    target_entities[entity_id] = entity
                    target_entities[entity_id]["brat_id"] = entity_id

                    entity_id += 1

                for brat_id, relation in second_relations.items():
                    target_relations[relation_id] = relation
                    target_relations[relation_id]["arg1"] = mapping[relation["arg1"]]
                    target_relations[relation_id]["arg2"] = mapping[relation["arg2"]]

                    relation_id += 1

                att_id = 1

                with open(target_ann, "w", encoding="UTF-8") as output_file:
                    for k, v in target_entities.items():
                        output_file.write("T{}\t{} {}\t{}\n".format(
                            k,
                            v["type"],
                            ";".join(["{} {}".format(i, j) for i, j in v["spans"]]),
                            v["text"]
                        ))

                        for att_name, att_value in v["attributes"].items():
                            output_file.write("A{}\t{} T{} {}\n".format(
                                att_id,
                                att_name,
                                k,
                                att_value
                            ))
                            att_id += 1

                    for k, v in target_relations.items():
                        output_file.write("R{}\t{} Arg1:T{} Arg2:T{}\n".format(
                            k,
                            v["type"],
                            v["arg1"],
                            v["arg2"]
                        ))

    generate_brat_conf_files(output_path)
