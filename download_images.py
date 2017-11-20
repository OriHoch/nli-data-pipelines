from datapackage_pipelines.wrapper import ingest, spew
from dotenv import load_dotenv, find_dotenv
import requests, json, logging, os, re, base64
from google.cloud.storage.client import Client
from google.oauth2 import service_account
load_dotenv(find_dotenv())


def main():
    parameters, datapackage, resources = ingest()
    aggregations = {"stats": {},
                    "sysnum_images": {}}
    resources = list(resources)
    for descriptor in datapackage["resources"]:
        descriptor["schema"]["fields"] = [{"name": "manifest_label", "type": "string"},
                                          {"name": "manifest_sysnum", "type": "string"},
                                          {"name": "resource_id", "type": "string"},
                                          {"name": "resource_type", "type": "string"},
                                          {"name": "resource_format", "type": "string"},
                                          {"name": "resource_width", "type": "number"},
                                          {"name": "resource_height", "type": "number"},
                                          {"name": "resource_filepath", "type": "string"},
                                          {"name": "url", "type": "string"}]

    def get_resource(resource, descriptor):
        if os.environ.get("GCS_SERVICE_ACCOUNT_B64_KEY"):
            credentials_info = json.loads(base64.decodebytes(os.environ["GCS_SERVICE_ACCOUNT_B64_KEY"].encode()))
            credentials = service_account.Credentials.from_service_account_info(credentials_info)
            gcs = Client(project=os.environ["GCS_PROJECT"], credentials=credentials)
            bucket = gcs.bucket(os.environ["GCS_IMAGES_BUCKET"])
        else:
            bucket = None
        for i, row in enumerate(resource):
            url = row["resource_id"]
            if not url.startswith("http://iiif.nli.org.il/IIIFv21/") or not url.endswith("/full/max/0/default.jpg"):
                raise Exception("unknown url: {}".format(url))
            image_id = url.replace("http://iiif.nli.org.il/IIIFv21/", "").replace("/full/max/0/default.jpg", "")
            if image_id != row["id"]:
                raise Exception("Invalid row id {} or url {}".format(row["id"], url))
            sysnum = row["manifest_sysnum"]
            if str(sysnum) not in aggregations["sysnum_images"]:
                aggregations["sysnum_images"][str(sysnum)] = {}
                filepath = sysnum+".jpg"
            else:
                filepath = sysnum + "_" + image_id + ".jpg"
            if bucket:
                blob = bucket.blob(filepath)
                if not blob.exists():
                    blob.upload_from_string(requests.get(url).content)
                blob.make_public()
                public_url = blob.public_url
            else:
                public_url = "https://storage.googleapis.com/nli-images/"+filepath
            yield {"manifest_label": row["manifest_label"],
                   "manifest_sysnum": row["manifest_sysnum"],
                   "resource_id": row["resource_id"],
                   "resource_type": row["resource_type"],
                   "resource_format": row["resource_format"],
                   "resource_width": row["resource_width"],
                   "resource_height": row["resource_height"],
                   "resource_filepath": filepath,
                   "url": public_url}

    def get_resources():
        for resource, descriptor in zip(resources, datapackage["resources"]):
            yield get_resource(resource, descriptor)

    spew(datapackage,
         get_resources(),
         aggregations["stats"])


if __name__ == "__main__":
    main()
