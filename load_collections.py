from datapackage_pipelines.wrapper import ingest, spew
from datapackage_pipelines.utilities.resources import PROP_STREAMING
from dotenv import load_dotenv, find_dotenv
import requests, json, logging


load_dotenv(find_dotenv())


def main():
    parameters, datapackage, resources = ingest()
    aggregations = {"stats": {}}
    collections = {}
    for descriptor, resource in zip(datapackage["resources"], resources):
        if descriptor["name"] == "collections":
            collections = list(resource)
        else:
            list(resource)
    datapackage["resources"] = []
    for collection in collections:
        datapackage["resources"].append({PROP_STREAMING: True,
                                         "name": collection["id"],
                                         "path": "{}.csv".format(collection["id"]),
                                         "schema": {"fields": [{"name": "label", "type": "string"},
                                                               {"name": "manifest", "type": "string"}]}})

    def get_resource(collection):
        for member in json.loads(requests.get(collection["json"]).content)["members"]:
            yield {"label": member["label"],
                   "manifest": member["@id"]}

    spew(datapackage,
         (get_resource(collection) for collection in collections),
         aggregations["stats"])


if __name__ == "__main__":
    main()
