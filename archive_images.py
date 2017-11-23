from datapackage_pipelines.wrapper import ingest, spew
from datapackage_pipelines.utilities.resources import PROP_STREAMING
from dotenv import load_dotenv, find_dotenv
import logging, requests, os, random, time, queue, threading
import requests.adapters
load_dotenv(find_dotenv())


def download_retry(requests_session, url, retry_num=1, max_retries=5):
    try:
        return requests_session.get(url).content
    except Exception:
        logging.exception("Exception downloading from url {}".format(url))
        if max_retries is None:
            raise
        elif retry_num > max_retries:
            logging.info("attempt {} failed, giving up".format(retry_num))
            raise
        else:
            sleep_time = random.choice(range(20,50))
            logging.info("attempt {} failed, sleeping {} seconds and retrying".format(retry_num, sleep_time))
            time.sleep(sleep_time)
            return download_retry(requests_session, url, retry_num+1)


def start_downloader(poolsize, numthreads, worker=None, max_retries=None):
        session = requests.session()
        session.mount("http://", requests.adapters.HTTPAdapter(pool_connections=poolsize, pool_maxsize=poolsize))
        session.mount("https://", requests.adapters.HTTPAdapter(pool_connections=poolsize, pool_maxsize=poolsize))
        q = queue.Queue()
        threads = []
        def thread_worker():
            while True:
                item = q.get()
                if item is None:
                    break
                # if worker callback is provided, it must return True to override the default functionality
                if not worker or not worker(item):
                    url, filepath = item
                    if not os.path.exists(filepath):
                        logging.info("Downloading {} -> {}".format(url, filepath))
                        os.makedirs(os.path.dirname(filepath), exist_ok=True)
                        with open(filepath, "wb") as f:
                            content = download_retry(session, url, max_retries=max_retries)
                            f.write(content)
                q.task_done()
        for i in range(numthreads):
            t = threading.Thread(target=thread_worker)
            t.start()
            threads.append(t)


def get_resource(resource, aggregations, collection):
    requests_session = requests.session()
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
            filepath = sysnum + ".jpg"
        else:
            filepath = sysnum + "_" + image_id + ".jpg"
        downloaded = False
        url = "https://storage.googleapis.com/nli-images/" + filepath
        cache_filepath = os.environ["PIPELINES_HOST_DATA_CACHE_PATH"] + os.path.join("image-archive", collection, filepath)
        logging.info("{} -> {}".format(url, cache_filepath))
        if not os.path.exists(cache_filepath):
            os.makedirs(os.path.dirname(cache_filepath), exist_ok=True)
            with open(cache_filepath, "wb") as f:
                f.write(requests_session.get(url).content)
                downloaded = True
        yield {"manifest_label": row["manifest_label"],
               "manifest_sysnum": row["manifest_sysnum"],
               "resource_id": row["resource_id"],
               "resource_type": row["resource_type"],
               "resource_format": row["resource_format"],
               "resource_width": row["resource_width"],
               "resource_height": row["resource_height"],
               "resource_filepath": filepath,
               "url": url,
               "downloaded": downloaded}


def main():
    parameters, datapackage, resources = ingest()
    aggregations = {"stats": {}, "sysnum_images": {}}
    fields = [{"name": "manifest_label", "type": "string"},
              {"name": "manifest_sysnum", "type": "string"},
              {"name": "resource_id", "type": "string"},
              {"name": "resource_type", "type": "string"},
              {"name": "resource_format", "type": "string"},
              {"name": "resource_width", "type": "number"},
              {"name": "resource_height", "type": "number"},
              {"name": "resource_filepath", "type": "string"},
              {"name": "url", "type": "string"},
              {"name": "downloaded", "type": "boolean"}]
    output_resources = []
    output_descriptors = []
    for resource, descriptor in zip(resources, datapackage["resources"]):
        logging.info("creating images archive for collection {}".format(descriptor["name"]))
        output_resources.append(get_resource(resource, aggregations, descriptor["name"]))
        output_descriptors.append({PROP_STREAMING: True,
                                 "name": descriptor["name"],
                                 "path": "{}.csv".format(descriptor["name"]),
                                 "schema": {"fields": fields}})
    datapackage["resources"] = output_descriptors
    spew(datapackage, output_resources, aggregations["stats"])


if __name__ == "__main__":
    main()
