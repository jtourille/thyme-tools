import copy
import json
import logging
import os
import re
import time

from lxml import etree

from .brat import generate_brat_conf_files, parse_ann_file
from .utils import ensure_dir

REGEX_TEMPORAL_FILE = re.compile(r".*\.Temporal-(Relation|Entity).(gold|system).completed.xml")


def anafora_to_brat(input_anafora_path: str = None,
                    input_thyme_path: str = None,
                    output_brat_path: str = None,
                    preproc_file_path: str = None) -> None:
    """
    Convert a THYME corpus part to brat format

    Args:
        input_anafora_path (str): annotation path (anafora format)
        input_thyme_path (str): corpus path (text format)
        output_brat_path(str): output path where brat files will be created
        preproc_file_path (str): preprocessing filepath (json format)

    Returns:
        None
    """

    corrected_entities_nb = 0

    # Loading json content
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
                corrected_entities, nb = correct_entity_spans(entities, target_txt_file)
                corrected_entities, last_entity_id = assign_brat_id(corrected_entities)

                corrected_entities_nb += nb

                # Computing brat relations and assigning a brat ID to relations
                corrected_relations = compute_brat_relations(relations, corrected_entities)
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

    logging.info("Number of corrected entities: {}".format(corrected_entities_nb))

    # Generating a set of brat configuration files for the current directory
    generate_brat_conf_files(os.path.abspath(output_brat_path))


def assign_brat_id(elements: list = None,
                   start: int = 1) -> (list, int):
    """
    Assign a brat ID for elements in a list of dictionaries

    Args:
        elements (list): element list
        start (int): starting index

    Returns:
        (list, int): element list with brat IDs and last ID
    """

    last_id = 0

    for i, el in enumerate(elements, start=start):
        el["brat_id"] = i
        last_id = i

    return elements, last_id


def brat_to_anafora(input_brat_dir: str = None,
                    output_anafora_dir: str = None) -> None:
    """
    Convert a THYME corpus part from brat to anafora

    Args:
        input_brat_dir (str): annotation path (brat format)
        output_anafora_dir (str): output path where anafora files will be created

    Returns:
        None
    """

    for root, dirs, files in os.walk(os.path.abspath(input_brat_dir)):
        for filename in files:
            if re.match("^.*\.ann$", filename):

                document_id = filename.split(".")[0]

                # Fetching entities and relations from files and converting to anafora format
                source_ann_file = os.path.join(root, filename)
                entities, relations = parse_ann_file(source_ann_file)
                ana_entities, ana_relations = convert_brat_payload_to_anafora_payload(entities, relations, document_id)

                # Building target directory
                target_dir = os.path.join(os.path.abspath(output_anafora_dir), document_id)
                ensure_dir(target_dir)

                # Creating xml payload
                target_file = os.path.join(target_dir, "{}.Temporal-Relation.system.completed.xml".format(document_id))
                xml_payload = generate_payload(ana_entities, ana_relations, document_id)

                # Writing payload to disk
                tree = etree.ElementTree(xml_payload)
                tree.write(target_file, pretty_print=True, xml_declaration=True, encoding='UTF-8')


def compute_brat_relations(source_relations: list = None,
                           corrected_entities: list = None) -> list:
    """
    Compute a brat relation list based on corrected entities and relations extracted from a THYME corpus document

    Args:
        source_relations (list): list of relations extracted from the document
        corrected_entities (list): corrected entities with brat IDs

    Returns:
        list: brat relations
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


def convert_brat_payload_to_anafora_payload(brat_entities: dict = None,
                                            brat_relations: dict = None,
                                            document_id: dict = None):
    """
    Convert a brat payload (entities and relations) to anafora format

    Args:
        brat_entities (dict): entities extracted from brat file
        brat_relations (dict): relations extracted from brat file
        document_id (str): document ID used for naming elements

    Returns:
        (list, list): entities and relations in anafora format
    """

    ana_entities = list()
    ana_relations = list()

    for brat_id, entity in brat_entities.items():
        current_entity = {
            "id": entity["attributes"]["AnaforaID"],
            "type": entity["type"],
            "span": entity["spans"],
            "properties": {k: v for k, v in entity["attributes"].items() if k != "AnaforaID"}
        }

        ana_entities.append(current_entity)

    for brat_id, relation in brat_relations.items():
        current_relation = {
            "id": "{}@r@{}@system".format(brat_id, document_id),
            "type": "TLINK",
            "properties": {
                "Source": brat_entities[relation["arg1"]]["attributes"]["AnaforaID"],
                "Target": brat_entities[relation["arg2"]]["attributes"]["AnaforaID"],
                "Type": relation["type"]
            }
        }

        ana_relations.append(current_relation)

    return ana_entities, ana_relations


def correct_and_copy_txt_file(source_txt_filepath: str = None,
                              target_txt_filepath: str = None,
                              preproc_payload: dict = None) -> None:
    """
    Copy and correct a THYME corpus text file from one location to another location

    Args:
        source_txt_filepath (str): source THYME corpus text filepath
        target_txt_filepath (str): target THYME corpus text filepath
        preproc_payload (dict): preprocessing file content

    Returns:
        None
    """

    # Loading text file content
    content_src = open(os.path.abspath(source_txt_filepath), "r", encoding="UTF-8", newline='').read()

    # Fetching file corrections if available
    for filename in preproc_payload["replace"]:
        if filename == os.path.basename(source_txt_filepath):
            for begin, end, replacement in preproc_payload["replace"][filename]:
                content_src = content_src[:begin] + replacement + content_src[end:]

    # Copying modified content to target file
    with open(os.path.abspath(target_txt_filepath), "w", encoding="UTF-8") as output_file:
        output_file.write(content_src)


def correct_entity_spans(entities: list = None,
                         txt_filepath: str = None):
    """
    Correct entity span by removing leading and trailing spaces and line breaks.
    Add text span to entities.

    Args:
        entities (list): entity list extracted from the document
        txt_filepath (str): THYME document filepath (text format)

    Returns:
        list: corrected entity list
    """

    corrected_entities_nb = 0

    # Loading document content
    content = open(os.path.abspath(txt_filepath), "r", encoding="UTF-8").read()

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

            if offset_right > 0 or offset_left > 0:
                corrected_entities_nb += 1

            # Appending computed properties to entity
            current_entity["span"].append((begin, end))
            current_entity["text"].append(span_txt)

            # Sanity check: searching for line break within text spans
            if re.search("\n", span_txt):
                raise Exception("There is a sentence break in the middle of an entity in document {}: {}".format(
                    os.path.basename(txt_filepath),
                    entity
                ))

        # Appending corrected entity to list
        corrected_entities.append(current_entity)

    return corrected_entities, corrected_entities_nb


def generate_payload(entities: list = None,
                     relations: list = None,
                     document_id: list = None) -> etree.Element:
    """
    Generate xml payload for a thyme document

    Args:
        entities (list): list of entities
        relations (list): list of relations
        document_id (str): document ID

    Returns:
        etree.Element: xml payload

    """

    timestamp = time.strftime("%Y-%m-%d-%H:%M:%S")

    root = etree.Element("data")

    el_info = etree.SubElement(root, "info")

    el_savetime = etree.SubElement(el_info, "savetime")
    el_savetime.text = timestamp

    el_progress = etree.SubElement(el_info, "progress")
    el_progress.text = "completed"

    el_annotations = etree.SubElement(root, "annotations")

    for entity in entities:
        el_entity = etree.SubElement(el_annotations, "entity")

        el_id = etree.SubElement(el_entity, "id")
        el_id.text = entity["id"]

        el_span = etree.SubElement(el_entity, "span")
        el_span.text = ";".join(["{},{}".format(b, e) for b, e in entity["span"]])

        el_type = etree.SubElement(el_entity, "type")
        el_type.text = entity["type"]

        el_parents_type = etree.SubElement(el_entity, "parentsType")
        el_parents_type.text = "TemporalEntities"

        el_properties = etree.SubElement(el_entity, "properties")
        for att_tag, att_value in entity["properties"].items():
            el_attribute = etree.SubElement(el_properties, att_tag)
            el_attribute.text = att_value

    relation_id = 1

    for relation in relations:
        el_relation = etree.SubElement(el_annotations, "relation")

        el_id = etree.SubElement(el_relation, "id")
        el_id.text = "{}@r@{}@system".format(relation_id, document_id)

        el_type = etree.SubElement(el_relation, "type")
        el_type.text = relation["type"]

        relation_id += 1

        el_parents_type = etree.SubElement(el_relation, "parentsType")
        el_parents_type.text = "TemporalRelations"

        el_properties = etree.SubElement(el_relation, "properties")
        for att_tag, att_value in relation["properties"].items():
            el_attribute = etree.SubElement(el_properties, att_tag)
            el_attribute.text = str(att_value)

    return root


def get_anafora_entities(source_anafora_filepath: str = None) -> list:
    """
    Extract entities from a THYME corpus anafora file

    Args:
        source_anafora_filepath (str): source anafora filepath

    Returns:
        list: entity list
    """

    # Parsing xml file
    tree = etree.parse(source_anafora_filepath)
    root = tree.getroot()

    # Finding annotations element
    annotations = root.find("./annotations")

    # Sanity check, raising exception if there is a non-empty adjudication element
    adjudication = root.find("./adjudication")
    if adjudication is not None:
        if len(adjudication) > 0:
            raise Exception("The file {} is marked as 'completed' but contains adjudication annotations".format(
                os.path.basename(source_anafora_filepath)
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


def get_anafora_relations(source_anafora_filepath: str = None) -> list:
    """
    Extract relations from a THYME corpus anafora file

    Args:
        source_anafora_filepath (str): source anafora filepath

    Returns:
        list: relation list
    """

    # Parsing xml file
    tree = etree.parse(source_anafora_filepath)
    root = tree.getroot()

    # Finding annotations element
    annotations = root.find("./annotations")

    # Sanity check, raising exception if there is a non-empty adjudication element
    adjudication = root.find("./adjudication")
    if adjudication is not None:
        if len(adjudication) > 0:
            raise Exception("The file {} is marked as 'completed' but contains adjudication annotations".format(
                os.path.basename(source_anafora_filepath)
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


def is_in_progress(source_anafora_filepath: str = None) -> bool:
    """
    Check if the annotation process is 'completed' or 'in-progress'.
    Raise Exception if status is unknown.

    Args:
        source_anafora_filepath (str): anafora filepath

    Returns:
        bool: 'True' if annotation is in progress, 'False' otherwise
    """

    # Parsing xml file
    tree = etree.parse(source_anafora_filepath)
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
            source_anafora_filepath,
            progress.text
        ))
