from datapackage_pipelines.wrapper import ingest, spew
from dotenv import load_dotenv, find_dotenv
from common import get_image_file_path
load_dotenv(find_dotenv())


def main():
    parameters, datapackage, resources = ingest()
    for resource in datapackage["resources"]:
        if resource["name"] == "manifests":
            for field in resource["schema"]["fields"]:
                if field["name"] in ["attribution", "subject", "alternative_title", "title", "the_creator",
                                     "publisher", "label", "description"]:
                    field["es:type"] = "text"
                elif field["name"] in ["map", "sysnum", "language", "collection", "base"]:
                    field["es:type"] = "keyword"
                else:
                    field["es:type"] = "text"

    spew(datapackage, resources)


if __name__ == "__main__":
    main()
