from datapackage_pipelines.wrapper import ingest, spew
from dotenv import load_dotenv, find_dotenv
from common import get_image_file_path
load_dotenv(find_dotenv())


def main():
    parameters, datapackage, resources = ingest()
    aggregations = {}
    output_descriptors = []
    for resource_index, descriptor in enumerate(datapackage["resources"]):
        if parameters.get("start-at-resource-index") and resource_index <= parameters["start-at-resource-index"]:
            output_descriptors.append(descriptor)
        else:
            schema_kwargs = {}
            if parameters.get("primary-key"):
                schema_kwargs["primaryKey"] = parameters["primary-key"]
            output_descriptors.append(dict(descriptor,
                                           schema=dict(descriptor["schema"],
                                                       fields=[{"name": "collection",
                                                                "type": "string"},
                                                               {"name": "image_url",
                                                                "type": "string"}] + descriptor["schema"]["fields"],
                                                       **schema_kwargs),
                                           name=parameters["output-resource"],
                                           path=parameters["output-resource"] + '.csv',))
            break

    def get_rows(resource, descriptor_name):
        for i, row in enumerate(resource):
            if not parameters.get("limit") or i < parameters["limit"]:
                row["collection"] = descriptor_name
                if parameters.get("add-image-urls"):
                    sysnum = row["manifest_sysnum"]
                    image_id = row["id"]
                    row["image_url"] = "https://storage.googleapis.com/nli-images/" + get_image_file_path(sysnum, image_id, aggregations)
                yield row

    def get_resource(collection_resources):
        for i, resource in enumerate(collection_resources):
            for row in resource:
                yield row

    def get_resources():
        collection_resources = []
        for resource_index, resource_descriptor in enumerate(zip(resources, datapackage["resources"])):
            resource, descriptor = resource_descriptor
            if parameters.get("start-at-resource-index") and resource_index <= parameters["start-at-resource-index"]:
                yield resource
            else:
                collection_resources.append(get_rows(resource, descriptor["name"]))
        yield get_resource(collection_resources)


    spew(dict(datapackage, resources=output_descriptors), get_resources())


if __name__ == "__main__":
    main()
