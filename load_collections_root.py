from datapackage_pipelines.wrapper import ingest, spew
from datapackage_pipelines.utilities.resources import PROP_STREAMING
from dotenv import load_dotenv, find_dotenv
import requests, json, logging


load_dotenv(find_dotenv())


def get_collection_id(collection):
    return collection["@id"].replace("http://iiif.nli.org.il/collections/", "").replace(".json", "")


def main():
    parameters, datapackage, resources = ingest()
    aggregations = {
        "stats": {}
    }
    datapackage["resources"].append({PROP_STREAMING: True,
                                     "name": "collections",
                                     "path": "collections.csv",
                                     "schema": {"fields": [{"name": "id", "type": "string"},
                                                           {"name": "label", "type": "string"},
                                                           {"name": "json", "type": "string"}]}})

    def get_resource():
        root_data = json.loads(requests.get(parameters["root_url"]).content)
        for collection in root_data["collections"]:
            yield {"id": get_collection_id(collection),
                   "label": collection["label"],
                   "json": collection["@id"]}

    spew(datapackage, [get_resource()], aggregations["stats"])


if __name__ == "__main__":
    main()
