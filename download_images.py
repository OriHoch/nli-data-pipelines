from datapackage_pipelines.wrapper import ingest, spew
from dotenv import load_dotenv, find_dotenv
import logging, os
from gcs import get_bucket
from downloader import start_downloader, stop_downloader, download_retry
from common import get_resource_row_image, get_resource_row_image_schema
from functools import partial
load_dotenv(find_dotenv())


def incr_resource_stat(stats, resource_name, stat_id):
    key = "{}_{}".format(resource_name, stat_id)
    stats[key] += 1


def init_resource_stats(stats, descriptor):
    resource_name = descriptor["name"]
    stats["{}_processed_rows".format(resource_name)] = 0
    stats["{}_downloaded_rows".format(resource_name)] = 0


def download_blob(bucket, aggregations, collection, item, session):
    filepath, url = item
    logging.info("Downloading {} -> {}".format(url, filepath))
    blob = bucket.blob(filepath)
    blob.update()
    if not blob.exists() or blob.size is None or blob.size < 1:
        blob.upload_from_string(download_retry(session, url, max_retries=5))
    blob.make_public()
    incr_resource_stat(aggregations["stats"], collection, "downloaded_rows")
    logging.info(aggregations["stats"])


def get_images(resource, aggregations, collection, bucket, worker_queue):
    for i, row in enumerate(resource):
        if (
                        aggregations["stats"]["{}_processed_rows".format(collection)] > 500
                and aggregations["stats"]["{}_downloaded_rows".format(collection)] == 0
        ):
            logging.info("500 processed rows, 0 downloaded rows - skipping further downloads")
            skip_download = True
        else:
            skip_download = False
        image_row = get_resource_row_image(row, aggregations)
        filepath = image_row["resource_filepath"]
        url = image_row["resource_id"]
        if bucket:
            if skip_download:
                if worker_queue:
                    image_row["downloaded"] = False
            elif worker_queue:
                worker_queue.put((filepath, url))
            else:
                logging.info("Verifying {} -> {}".format(url, filepath))
                blob = bucket.blob(filepath)
                blob.update()
                image_row["downloaded"] = blob.exists() and blob.size is not None and blob.size > 0
                if image_row["downloaded"]:
                    incr_resource_stat(aggregations["stats"], collection, "downloaded_rows")
        incr_resource_stat(aggregations["stats"], collection, "processed_rows")
        logging.info(aggregations["stats"])
        yield image_row


def main():
    parameters, datapackage, resources = ingest()
    aggregations = {"stats": {},
                    "sysnum_images": {}}
    resources = list(resources)
    for descriptor in datapackage["resources"]:
        descriptor["schema"] = get_resource_row_image_schema()

    def get_resource(resource, descriptor):
        init_resource_stats(aggregations["stats"], descriptor)
        bucket = get_bucket(*list(map(os.environ.get, ["GCS_SERVICE_ACCOUNT_B64_KEY",
                                                       "GCS_IMAGES_BUCKET",
                                                       "GCS_PROJECT"])))
        queue, threads = None, None
        if not os.environ.get("GCS_DISABLE_DOWNLOAD"):
            numthreads = int(os.environ.get("DOWNLOAD_IMAGES_NUM_THREADS", "5"))
            poolsize = 20 if numthreads < 50 else int(numthreads / 2)
            logging.info("poolsize={}, numthreads={}".format(poolsize, numthreads))
            queue, threads = start_downloader(poolsize, numthreads,
                                              worker=partial(download_blob, bucket, aggregations, descriptor["name"]),
                                              max_retries=5)
        yield from get_images(resource, aggregations, descriptor["name"], bucket, queue)
        if queue:
            stop_downloader(queue, threads, int(os.environ.get("DOWNLOAD_IMAGES_NUM_THREADS", "5")))

    def get_resources():
        for resource, descriptor in zip(resources, datapackage["resources"]):
            yield get_resource(resource, descriptor)

    spew(datapackage,
         get_resources(),
         aggregations["stats"])


if __name__ == "__main__":
    main()
