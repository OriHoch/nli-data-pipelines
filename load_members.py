from datapackage_pipelines.wrapper import ingest, spew
from datapackage_pipelines.utilities.resources import PROP_STREAMING
from dotenv import load_dotenv, find_dotenv
import requests, json, logging


load_dotenv(find_dotenv())


def main():
    parameters, datapackage, resources = ingest()
    aggregations = {"stats": {}}
    aggregations["first_rows"] = {}
    aggregations["first_row_jsons"] = {}
    resources = list(resources)
    for resource, descriptor in zip(resources, datapackage["resources"]):
        collection = descriptor["name"]
        first_row = next(resource)
        aggregations["first_rows"][collection] = first_row
        first_row_json = json.loads(requests.get(first_row["manifest"]).content)
        aggregations["first_row_jsons"][collection] = first_row_json
        descriptor["schema"]["fields"] = [{"name": m["label"], "type": "string"} for m in first_row_json["metadata"]]

    def get_resource(resource, descriptor):
        collection = descriptor["name"]
        first_row, first_row_json = aggregations["first_rows"][collection], aggregations["first_row_jsons"][collection]
        yield {m["label"]: m["value"] for m in first_row_json["metadata"]}
        for row in resource:
            row_json = json.loads(requests.get(row["manifest"]).content)
            yield {m["label"]: str(m["value"]) for m in row_json["metadata"]}

    def get_resources():
        for resource, descriptor in zip(resources, datapackage["resources"]):
            yield get_resource(resource, descriptor)

    spew(datapackage,
         get_resources(),
         aggregations["stats"])


if __name__ == "__main__":
    main()
