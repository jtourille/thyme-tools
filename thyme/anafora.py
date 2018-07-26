import copy
import json
import logging
import os
import re

from lxml import etree

from .brat import generate_brat_conf_files

REGEX_TEMPORAL_FILE = re.compile(".*\.Temporal-(Relation|Entity).(gold|system).completed.xml")


def anafora_to_brat(input_anafora_path, input_thyme_path, output_brat_path, preproc_file_path):
    """
    Convert a THYME corpus part to brat format
    :param input_anafora_path: annotations path (anafora format)
    :param input_thyme_path: corpus path (text format)
    :param output_brat_path: output path where brat files will be written
    :param preproc_file_path: preprocessing option file path (json file)
    :return: nothing
    """

    preproc_payload = json.load(open(os.path.abspath(preproc_file_path), "r", encoding="UTF-8"))

    for root, dirs, files in os.walk(os.path.abspath(input_anafora_path)):
        for filename in files:
            if REGEX_TEMPORAL_FILE.match(filename):

                # Computing source file paths (txt and anafora formats)
                source_anafora_file = os.path.join(root, filename)
                source_txt_file = os.path.join(
                    os.path.abspath(input_thyme_path),
                    filename.split(".")[0]
                )

                # Checking is text annotation is in progress, skipping file if it is the case
                if is_in_progress(source_anafora_file):
                    logging.info("Skipping file {}. Reason: annotation in progress.".format(
                        os.path.basename(source_anafora_file)
                    ))
                    continue

                # Computing target brat file paths
                target_ann_file = os.path.join(
                    os.path.abspath(output_brat_path),
                    "{}.ann".format(filename.split(".")[0])
                )
                target_txt_file = os.path.join(
                    os.path.abspath(output_brat_path),
                    "{}.txt".format(filename.split(".")[0])
                )

                # Copying and correcting if necessary text document
                correct_and_copy_txt_file(source_txt_file, target_txt_file, preproc_payload)

                # Fetching entities and relations from anofora file
                entities = get_anafora_entities(source_anafora_file)
                relations = get_anafora_relations(source_anafora_file)

                # Correcting entity spans and assigning a brat ID to entities
                corrected_entities = correct_entity_spans(entities, target_txt_file)
                corrected_entities, last_entity_id = assign_brat_id(corrected_entities)

                # Computing brat relations and assigning a brat ID to relations
                corrected_relations = compute_brat_relation(relations, corrected_entities)
                corrected_relations, last_relation_id = assign_brat_id(corrected_relations)

                property_id = 1

                # Writing relations, entities and attributes to file
                with open(target_ann_file, "w", encoding="UTF-8") as output_file:

                    # Entities
                    for entity in corrected_entities:
                        output_file.write(
                            "T{}\t{} {}\t{}\n".format(
                                entity["brat_id"],
                                entity["type"],
                                ";".join(["{} {}".format(begin, end) for begin, end in entity["span"]]),
                                " ".join(entity["text"])
                            )
                        )

                        # Entity attributes
                        for prop_name, prop_value in entity["properties"].items():
                            output_file.write(
                                "A{}\t{} T{} {}\n".format(
                                    property_id,
                                    prop_name,
                                    entity["brat_id"],
                                    prop_value
                                )
                            )

                            property_id += 1

                        output_file.write(
                            "A{}\t{} T{} {}\n".format(
                                property_id,
                                "AnaforaID",
                                entity["brat_id"],
                                entity["id"]
                            )
                        )

                        property_id += 1

                    # Relations
                    for relation in corrected_relations:
                        output_file.write(
                            "R{}\t{} Arg1:T{} Arg2:T{}\n".format(
                                relation["brat_id"],
                                relation["brat_name"],
                                relation["brat_arg1"],
                                relation["brat_arg2"]
                            )
                        )

    # Generating a set of brat configuration files for the current directory
    generate_brat_conf_files(os.path.abspath(output_brat_path))


def assign_brat_id(elements, start=1):
    """
    Assign a brat ID for elements of a list of dictionaries
    :param start:
    :param elements: element list
    :return: element list with brat IDs
    """

    last_id = 0

    for i, el in enumerate(elements, start=start):
        el["brat_id"] = i
        last_id = i

    return elements, last_id


def compute_brat_relation(source_relations, corrected_entities):
    """
    Compute a brat relation list based on corrected entities and relations extracted from
    a THYME corpus document
    :param source_relations: extracted relations
    :param corrected_entities: corrected entities
    :return: extracted relations with brat properties
    """

    # Building entity index
    entity_index = [entity["id"] for entity in corrected_entities]

    corrected_relations = list()

    # Processing relations
    for relation in source_relations:
        current_relation = copy.deepcopy(relation)

        # Fetching source and target entities from current relation
        source_entity = current_relation["properties"]["Source"]
        target_entity = current_relation["properties"]["Target"]

        # Computing brat name, arg1 and arg2 based on entity index and relation type
        current_relation["brat_arg1"] = corrected_entities[entity_index.index(source_entity)]["brat_id"]
        current_relation["brat_arg2"] = corrected_entities[entity_index.index(target_entity)]["brat_id"]
        current_relation["brat_name"] = current_relation["properties"]["Type"]

        # Appending current relation to list
        corrected_relations.append(current_relation)

    return corrected_relations


def correct_and_copy_txt_file(source_txt_file, target_txt_file, preproc_payload):
    """
    Copy and correct a THYME corpus text file from one location to another location
    :param source_txt_file: source THYME corpus text file
    :param target_txt_file: target THYME corpus text file
    :param preproc_payload: preprocessing option file (contains corrections if applicable)
    :return: nothing
    """

    # Loading text file content
    content_src = open(os.path.abspath(source_txt_file), "r", encoding="UTF-8", newline='').read()

    # Fetching file corrections if available
    for filename in preproc_payload["replace"]:
        if filename == os.path.basename(source_txt_file):
            for begin, end, replacement in preproc_payload["replace"][filename]:
                content_src = content_src[:begin] + replacement + content_src[end:]

    # Copying modified content to target file
    with open(os.path.abspath(target_txt_file), "w", encoding="UTF-8") as output_file:
        output_file.write(content_src)


def correct_entity_spans(entities, txt_file_path):
    """
    Correct entity span by removing leading and trailing spaces and line breaks.
    Add text span to entities.
    :param entities: document entity list
    :param txt_file_path: document path (text format)
    :return: corrected entity list
    """

    # Loading document content
    content = open(os.path.abspath(txt_file_path), "r", encoding="UTF-8").read()

    corrected_entities = list()

    # Processing entities
    for entity in entities:

        # Copying entity, clearing span and creating text property
        current_entity = copy.deepcopy(entity)
        current_entity["span"].clear()
        current_entity["text"] = list()

        # Correcting span
        for span in sorted(entity["span"]):
            begin = span[0]
            end = span[1]

            span_txt = content[begin:end]

            # Removing trailing '\n' and ' ' and computing new right boundary
            span_txt_rstrip = span_txt.rstrip("\n ")
            offset_right = end - begin - len(span_txt_rstrip)

            # Removing leading '\n' and ' ' and computing new left boundary
            span_txt_lstrip = span_txt.lstrip("\n ")
            offset_left = end - begin - len(span_txt_lstrip)

            # Computing new offsets and extracting related text span
            begin += offset_left
            end -= offset_right
            span_txt = content[begin:end]

            # Appending computed properties to entity
            current_entity["span"].append((begin, end))
            current_entity["text"].append(span_txt)

            # Sanity check: searching for line break within text spans
            if re.search("\n", span_txt):
                raise Exception("There is a sentence break in the middle of an entity in document {}: {}".format(
                    os.path.basename(txt_file_path),
                    entity
                ))

        # Appending corrected entity to list
        corrected_entities.append(current_entity)

    return corrected_entities


def get_anafora_entities(source_anafora_file):
    """
    Extract entities from a THYME corpus anafora file
    :param source_anafora_file: source anafora file
    :return: list of entities
    """

    # Parsing xml file
    tree = etree.parse(source_anafora_file)
    root = tree.getroot()

    # Finding annotations element
    annotations = root.find("./annotations")

    # Sanity check, raising exception if there is a non-empty adjudication element
    adjudication = root.find("./adjudication")
    if adjudication is not None:
        if len(adjudication) > 0:
            raise Exception("The file {} is marked as 'completed' but contains adjudication annotations".format(
                os.path.basename(source_anafora_file)
            ))

    # Fetching entity elements from annotation element
    entities = annotations.findall("./entity")

    extracted_entities = list()

    # Processing entities
    for entity in entities:

        # Fetching entity ID, span and type
        current_entity_id = entity.find("./id").text
        current_entity_span = entity.find("./span").text
        current_entity_type = entity.find("./type").text

        # Fetching entity properties
        current_entity_properties = dict()
        for child in entity.find("./properties"):
            current_entity_properties[child.tag] = child.text

        # Creating entity object
        current_entity = {
            "id": current_entity_id,
            "type": current_entity_type,
            "properties": current_entity_properties,
            "span": list()
        }

        # Processing entity span
        for span in current_entity_span.split(";"):
            current_entity["span"].append(
                (int(span.split(",")[0]), int(span.split(",")[1]))
            )

        # Adding current entity to entity list
        extracted_entities.append(current_entity)

    return extracted_entities


def get_anafora_relations(source_anafora_file):
    """
    Extract relations from a THYME corpus anafora file
    :param source_anafora_file: source anafora file
    :return: list of relations
    """

    # Parsing xml file
    tree = etree.parse(source_anafora_file)
    root = tree.getroot()

    # Finding annotations element
    annotations = root.find("./annotations")

    # Sanity check, raising exception if there is a non-empty adjudication element
    adjudication = root.find("./adjudication")
    if adjudication is not None:
        if len(adjudication) > 0:
            raise Exception("The file {} is marked as 'completed' but contains adjudication annotations".format(
                os.path.basename(source_anafora_file)
            ))

    # Fetching relation elements from annotations element
    relations = annotations.findall("./relation")

    extracted_relations = list()

    # Processing relations
    for relation in relations:

        # Fetching relation ID and span
        current_relation_id = relation.find("./id").text
        current_relation_type = relation.find("./type").text

        # Fetching relation properties
        current_entity_properties = dict()
        for child in relation.find("./properties"):
            current_entity_properties[child.tag] = child.text

        # Creating relation object
        current_relation = {
            "id": current_relation_id,
            "type": current_relation_type,
            "properties": current_entity_properties,
        }

        # Adding current relation to relation list
        extracted_relations.append(current_relation)

    return extracted_relations


def is_in_progress(source_anafora_file):
    """
    Check if the annotation process is 'completed' or 'in-progress'.
    Raise Exception if status is unknown.
    :param source_anafora_file: anafora file path
    :return: 'True' if annotation is in progress, 'False' otherwise
    """

    # Parsing xml file
    tree = etree.parse(source_anafora_file)
    root = tree.getroot()

    # Fetching progress information element
    progress = root.find("./info/progress")

    # Checking progress information element value
    if progress.text == "in-progress":
        return True

    elif progress.text == "completed":
        return False

    else:
        raise Exception("Invalid progress value for file {}: {}".format(
            source_anafora_file,
            progress.text
        ))
