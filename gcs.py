from google.cloud.storage.client import Client
from google.oauth2 import service_account
import json, base64


def get_bucket(service_account_b64_key, bucket_name, google_project):
    if service_account_b64_key:
        assert bucket_name and google_project, "missing required GCS configurations"
        credentials_info = json.loads(base64.decodebytes(service_account_b64_key.encode()))
        credentials = service_account.Credentials.from_service_account_info(credentials_info)
        gcs = Client(project=google_project, credentials=credentials)
        return gcs.bucket(bucket_name)
    else:
        return None
