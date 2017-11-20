from datapackage_pipelines.wrapper import ingest, spew
from dotenv import load_dotenv, find_dotenv
import os, logging, json, requests
load_dotenv(find_dotenv())


string_field = lambda name: {"name": name, "type": "string"}
array_field = lambda name: {"name": name, "type": "array"}
number_field = lambda name: {"name": name, "type": "number"}


base_fields = list(map(string_field, ["description", "label", "title", "publisher", "base",
                                      "the_creator", "creation_date", "type", "format",
                                      "language", "sysnum", "related"]))
base_fields += list(map(array_field, ["attribution", "subject", "alternative_title"]))

collection_schema_fields = {
    "bitmuna": base_fields + [],
    "danhadani": base_fields + [],
    "ephemera": base_fields + [],
    "kettubot": base_fields + [],
    "manuscripts": base_fields + [],
    "maps": base_fields + [],
    "tm": base_fields + [],
    "tma": base_fields + [],
    "wahrman": base_fields + [],
}


def get_manifest_file(manifest_file):
    if os.environ.get("PIPELINES_HOST_DATA_CACHE_PATH"):
        return manifest_file.replace("data/cache", os.environ["PIPELINES_HOST_DATA_CACHE_PATH"])
    else:
        return manifest_file

def get_sequence_file(sequence_file):
    if os.environ.get("PIPELINES_HOST_DATA_CACHE_PATH"):
        return sequence_file.replace("data/cache", os.environ["PIPELINES_HOST_DATA_CACHE_PATH"])
    else:
        return sequence_file

def get_manifest_metadata(manifest, label, optional=False):
    for m in manifest["metadata"]:
        if m["label"] == label:
            return m["value"]
    if optional:
        return None
    else:
        raise Exception("Couldn't find manifest metadata label {}".format(label))


def get_as_array(value):
    if type(value) is list:
        return value
    else:
        return [value]


def main():
    parameters, datapackage, resources = ingest()
    aggregations = {"stats": {}}
    resources = list(resources)

    for descriptor in datapackage["resources"]:
        if parameters.get("parse-sequences"):
            descriptor["schema"] = {"fields": list(map(string_field, ["manifest_label", "manifest_sysnum",
                                                                      "sequence_id", "sequence_label", "canvas_id",
                                                                      "canvas_label",
                                                                      "id", "type", "motivation", "resource_id",
                                                                      "resource_type", "resource_format", ])) +
                                              list(map(number_field, ["resource_width", "resource_height",
                                                                      "canvas_width", "canvas_height",]))}
        else:
            descriptor["schema"]["fields"] = collection_schema_fields[descriptor["name"]]

    def get_row(row, descriptor):
        with open(get_manifest_file(row["manifest_file"])) as f:
            manifest = json.load(f)
        sysnum = get_manifest_metadata(manifest, "SysNum")
        if parameters.get("parse-sequences"):
            try:
                for sequence_num, sequence in enumerate(manifest["sequences"]):
                    if "canvases" not in sequence:
                        sequence_file = get_sequence_file(os.path.join("data", "cache", "sequence_files",
                                                                       sysnum[3], sysnum[4:6], sysnum+".json"))
                        if not os.path.exists(sequence_file) or os.path.getsize(sequence_file) < 20:
                            logging.info("missing canvases for sequence {} of manifest sysnum {}".format(sequence_num,
                                                                                                         sysnum))
                            logging.info("downloading to sequence file: {}".format(sequence_file))
                            os.makedirs(os.path.dirname(sequence_file), exist_ok=True)
                            with open(sequence_file, "w") as f:
                                json.dump(json.loads(requests.get(sequence["@id"]).content.decode("utf-8")), f, indent=2, ensure_ascii=False)
                        with open(sequence_file) as f:
                            sequence = json.load(f)
                    if "canvases" not in sequence:
                        continue
                    for canvas in sequence["canvases"]:
                        for image in canvas["images"]:
                            yield {"manifest_label": manifest["label"],
                                   "manifest_sysnum": get_manifest_metadata(manifest, "SysNum"),
                                   "sequence_id": sequence["@id"],
                                   "sequence_label": sequence["label"],
                                   "canvas_id": canvas["@id"],
                                   "canvas_label": canvas["label"],
                                   "canvas_width": canvas["width"],
                                   "canvas_height": canvas["height"],
                                   "id": image["@id"],
                                   "type": image["@type"],
                                   "motivation": image["motivation"],
                                   "resource_id": image["resource"]["@id"],
                                   "resource_type": image["resource"]["@type"],
                                   "resource_format": image["resource"]["format"],
                                   "resource_height": image["resource"]["height"],
                                   "resource_width": image["resource"]["width"],}
            except Exception:
                logging.exception("Failed to parse manifest: {}".format(json.dumps(manifest, ensure_ascii=False, indent=2)))
                raise
        else:
            try:
                    row = {"attribution": get_as_array(manifest.get("attribution")),
                           "description": manifest.get("description"),
                           "label": manifest["label"],
                           "title": get_manifest_metadata(manifest, "Title"),
                           "publisher": get_manifest_metadata(manifest, "Publisher", optional=True),
                           "base": get_manifest_metadata(manifest, "Base"),
                           "subject": get_as_array(get_manifest_metadata(manifest, "Subject", optional=True)),
                           "the_creator": get_manifest_metadata(manifest, "The Creator", optional=True),
                           "creation_date": get_manifest_metadata(manifest, "Creation Date", optional=True),
                           "type": get_manifest_metadata(manifest, "Type"),
                           "format": get_manifest_metadata(manifest, "Format", optional=True),
                           "language": get_manifest_metadata(manifest, "Language", optional=True),
                           "sysnum": sysnum,
                           "alternative_title": get_as_array(get_manifest_metadata(manifest, "Alternative Title", optional=True)),
                           "related": manifest["related"], }
            except Exception:
                logging.exception("Failed to parse manifest: {}".format(json.dumps(manifest, ensure_ascii=False, indent=2)))
                raise
            yield row

    def get_resource(resource, descriptor):
        for row in resource:
            yield from get_row(row, descriptor)

    def get_resources():
        for resource, descriptor in zip(resources, datapackage["resources"]):
            yield get_resource(resource, descriptor)

    spew(datapackage,
         get_resources(),
         aggregations["stats"])


if __name__ == "__main__":
    main()
