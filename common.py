from contextlib import contextmanager
from tempfile import mkdtemp
import os


def get_resource_row_image_schema():
    return {"fields": [{"name": "manifest_label", "type": "string"},
                       {"name": "manifest_sysnum", "type": "string"},
                       {"name": "resource_id", "type": "string"},
                       {"name": "resource_type", "type": "string"},
                       {"name": "resource_format", "type": "string"},
                       {"name": "resource_width", "type": "number"},
                       {"name": "resource_height", "type": "number"},
                       {"name": "resource_filepath", "type": "string"},
                       {"name": "url", "type": "string"},
                       {"name": "downloaded", "type": "boolean"}]}


def get_image_file_path(sysnum, image_id, aggregations):
    aggregations.setdefault("sysnum_images", set())
    if str(sysnum) not in aggregations["sysnum_images"]:
        aggregations["sysnum_images"].add(str(sysnum))
        return sysnum + ".jpg"
    else:
        return sysnum + "_" + image_id + ".jpg"


def get_resource_row_image(resource_row, aggregations):
    url = resource_row["resource_id"]
    if not url.startswith("http://iiif.nli.org.il/IIIFv21/") or not url.endswith("/full/max/0/default.jpg"):
        raise Exception("unknown url: {}".format(url))
    image_id = url.replace("http://iiif.nli.org.il/IIIFv21/", "").replace("/full/max/0/default.jpg", "")
    if image_id != resource_row["id"]:
        raise Exception("Invalid row id {} or url {}".format(resource_row["id"], url))
    sysnum = resource_row["manifest_sysnum"]
    filepath = get_image_file_path(sysnum, image_id, aggregations)
    return {"manifest_label": resource_row["manifest_label"],
            "manifest_sysnum": resource_row["manifest_sysnum"],
            "resource_id": resource_row["resource_id"],
            "resource_type": resource_row["resource_type"],
            "resource_format": resource_row["resource_format"],
            "resource_width": resource_row["resource_width"],
            "resource_height": resource_row["resource_height"],
            "resource_filepath": filepath,
            "url": url,
            "downloaded": None}


@contextmanager
def temp_dir(*args, **kwargs):
    dir = mkdtemp(*args, **kwargs)
    try:
        yield dir
    except Exception:
        if os.path.exists(dir):
            os.rmdir(dir)
        raise


@contextmanager
def temp_file(*args, **kwargs):
    with temp_dir(*args, **kwargs) as dir:
        file = os.path.join(dir, "temp")
        try:
            yield file
        except Exception:
            if os.path.exists(file):
                os.unlink(file)
            raise
