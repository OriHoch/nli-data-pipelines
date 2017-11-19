from datapackage_pipelines.wrapper import ingest, spew
from dotenv import load_dotenv, find_dotenv
import requests, json, logging, os, re
load_dotenv(find_dotenv())

#                                 http://iiif.nli.org.il/IIIFv21/DOCID/NNL03_Bitmuna700134313/manifest
MANIFEST_URL_REGEX = re.compile('^http://iiif.nli.org.il/IIIFv21/DOCID/([A-Za-z0-9_]+[A-Za-z]([0-9]+))/manifest$')


def parse_row(row):
    manifest_url = row["manifest"]
    res = MANIFEST_URL_REGEX.findall(manifest_url)
    if not res or len(res) != 1 or len(res[0]) != 2:
        raise Exception("Failed to parse row manifest_url '{}'".format(manifest_url))
    else:
        doc_id = res[0][0]
        system_number = res[0][1]
        path_parts = doc_id.split("_")
        path_parts[-1] = path_parts[-1].replace(system_number, "")
        path_parts.append(system_number[:3])
        path_parts.append(system_number[3:6])
        path_parts.append(system_number)
        manifest_file = os.path.join("data", "cache", "manifest-files", *path_parts)+".json"
        if not os.path.exists(manifest_file) or os.path.getsize(manifest_file) < 5:
            logging.info("Downloading manifest file {} -> {}".format(row["manifest"], manifest_file))
            if os.path.exists(manifest_file):
                os.unlink(manifest_file)
            elif not os.path.exists(os.path.dirname(manifest_file)):
                os.makedirs(os.path.dirname(manifest_file), exist_ok=True)
            with open(manifest_file, "w") as f:
                json.dump(json.loads(requests.get(row["manifest"]).content.decode("utf-8")), f, indent=2, ensure_ascii=False)
        else:
            logging.info("Skipping download of existing manifest file {}".format(manifest_file))
        return {"manifest_url": manifest_url,
                "doc_id": doc_id,
                "system_number": system_number,
                "manifest_file": manifest_file}


def main():
    parameters, datapackage, resources = ingest()
    aggregations = {"stats": {}}
    resources = list(resources)
    for descriptor in datapackage["resources"]:
        descriptor["schema"]["fields"] = [{"name": "doc_id", "type": "string"},
                                          {"name": "system_number", "type": "string"},
                                          {"name": "manifest_url", "type": "string"},
                                          {"name": "manifest_file", "type": "string"}]

    def get_resources():
        for resource, descriptor in zip(resources, datapackage["resources"]):
            yield (parse_row(row) for row in resource)

    spew(datapackage,
         get_resources(),
         aggregations["stats"])


if __name__ == "__main__":
    main()
