from datapackage_pipelines.wrapper import ingest, spew
from dotenv import load_dotenv, find_dotenv
import requests, json, logging, os, re, base64
from google.cloud.storage.client import Client
from google.oauth2 import service_account
load_dotenv(find_dotenv())
import queue, threading, time, random
import requests.adapters


def download_retry(requests_session, url, retry_num=1):
    try:
        return requests_session.get(url).content
    except Exception:
        logging.exception("Exception downloading from url {}".format(url))
        if retry_num > 5:
            logging.info("attempt {} failed, giving up".format(retry_num))
            raise
        else:
            sleep_time = random.choice(range(20,50))
            logging.info("attempt {} failed, sleeping {} seconds and retrying".format(retry_num, sleep_time))
            time.sleep(sleep_time)
            return download_retry(requests_session, url, retry_num+1)


def incr_resource_stat(stats, resource_name, stat_id):
    key = "{}_{}".format(resource_name, stat_id)
    stats[key] += 1


def init_resource_stats(stats, descriptor):
    resource_name = descriptor["name"]
    stats["{}_processed_rows".format(resource_name)] = 0
    stats["{}_downloaded_rows".format(resource_name)] = 0


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
                                          {"name": "url", "type": "string"},
                                          {"name": "downloaded", "type": "boolean"}]

    def get_resource(resource, descriptor):
        init_resource_stats(aggregations["stats"], descriptor)
        if os.environ.get("GCS_SERVICE_ACCOUNT_B64_KEY"):
            credentials_info = json.loads(base64.decodebytes(os.environ["GCS_SERVICE_ACCOUNT_B64_KEY"].encode()))
            credentials = service_account.Credentials.from_service_account_info(credentials_info)
            gcs = Client(project=os.environ["GCS_PROJECT"], credentials=credentials)
            bucket = gcs.bucket(os.environ["GCS_IMAGES_BUCKET"])
        else:
            bucket = None
        if not os.environ.get("GCS_DISABLE_DOWNLOAD"):
            requests_session = requests.session()
            poolsize = int(int(os.environ.get("DOWNLOAD_IMAGES_NUM_THREADS", "5")) / 2)
            if poolsize < 20:
                poolsize = 20
            requests_session.mount("http://", requests.adapters.HTTPAdapter(pool_connections=poolsize, pool_maxsize=poolsize))
            requests_session.mount("https://", requests.adapters.HTTPAdapter(pool_connections=poolsize, pool_maxsize=poolsize))
            q = queue.Queue()
            threads = []
            def thread_worker():
                while True:
                    item = q.get()
                    if item is None:
                        break
                    filepath, url = item
                    logging.info("Downloading {} -> {}".format(url, filepath))
                    blob = bucket.blob(filepath)
                    blob.update()
                    if not blob.exists() or blob.size is None or blob.size < 1:
                        blob.upload_from_string(download_retry(requests_session, url))
                    blob.make_public()
                    incr_resource_stat(aggregations["stats"], descriptor["name"], "downloaded_rows")
                    logging.info(aggregations["stats"])
                    q.task_done()
            for i in range(int(os.environ.get("DOWNLOAD_IMAGES_NUM_THREADS", "5"))):
                t = threading.Thread(target=thread_worker)
                t.start()
                threads.append(t)
        for i, row in enumerate(resource):
            if (
                aggregations["stats"]["{}_processed_rows".format(descriptor["name"])] > 500
                and aggregations["stats"]["{}_downloaded_rows".format(descriptor["name"])] == 0
            ):
                logging.info("500 processed rows, 0 downloaded rows - skipping further downloads")
                skip_download = True
            else:
                skip_download = False
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
            downloaded = None
            if bucket:
                if skip_download:
                    if not os.environ.get("GCS_DISABLE_DOWNLOAD"):
                        downloaded = False
                elif not os.environ.get("GCS_DISABLE_DOWNLOAD"):
                    q.put((filepath, url))
                else:
                    logging.info("Verifying {} -> {}".format(url, filepath))
                    blob = bucket.blob(filepath)
                    blob.update()
                    downloaded = blob.exists() and blob.size is not None and blob.size > 0
                    if downloaded:
                        incr_resource_stat(aggregations["stats"], descriptor["name"], "downloaded_rows")
            incr_resource_stat(aggregations["stats"], descriptor["name"], "processed_rows")
            logging.info(aggregations["stats"])
            yield {"manifest_label": row["manifest_label"],
                   "manifest_sysnum": row["manifest_sysnum"],
                   "resource_id": row["resource_id"],
                   "resource_type": row["resource_type"],
                   "resource_format": row["resource_format"],
                   "resource_width": row["resource_width"],
                   "resource_height": row["resource_height"],
                   "resource_filepath": filepath,
                   "url": "https://storage.googleapis.com/nli-images/"+filepath,
                   "downloaded": downloaded}
        if not os.environ.get("GCS_DISABLE_DOWNLOAD"):
            # block until all tasks are done
            q.join()
            # stop workers
            for i in range(int(os.environ.get("DOWNLOAD_IMAGES_NUM_THREADS", "5"))):
                q.put(None)
            for t in threads:
                t.join()

    def get_resources():
        for resource, descriptor in zip(resources, datapackage["resources"]):
            yield get_resource(resource, descriptor)

    spew(datapackage,
         get_resources(),
         aggregations["stats"])


if __name__ == "__main__":
    main()
