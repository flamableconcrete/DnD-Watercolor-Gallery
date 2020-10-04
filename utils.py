import mimetypes
import os
import sys
import zipfile
from pathlib import Path

# third party
import boto3
from azure.storage.blob import BlobServiceClient, ContentSettings
from boto3 import Session
from dotenv import load_dotenv

# local
from DirectoryClient import DirectoryClient

load_dotenv()
DO_SPACE = os.getenv("DO_SPACE")
DO_ACCESS_KEY_ID = os.getenv("DO_ACCESS_KEY_ID")
DO_SECRET_ACCESS_KEY = os.getenv("DO_SECRET_ACCESS_KEY")
AZURE_STORAGE_ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")


def azure_get_blob_service_client():
    blob_service_client = None
    try:
        blob_service_client = BlobServiceClient.from_connection_string(
            AZURE_STORAGE_CONNECTION_STRING
        )
    except Exception as ex:
        print(ex)
    return blob_service_client


def azure_backup_container(src_container, dest_container):
    blob_service_client = azure_get_blob_service_client()

    src_container_url = (
        f"https://{AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net/{src_container}"
    )
    src_container_client = DirectoryClient(
        AZURE_STORAGE_CONNECTION_STRING, src_container
    )
    dest_container_client = blob_service_client.get_container_client(dest_container)

    for blob in src_container_client.ls_files(path=""):
        blob_path = blob.replace("\\", "/")
        blob_url = f"{src_container_url}/{blob_path}"
        dest_blob = dest_container_client.get_blob_client(blob_path)
        print(f"Start copying: {blob_url}")
        dest_blob.start_copy_from_url(blob_url)

    # containers = blob_service_client.make_blob_url(src_container, "index.html")
    # return containers


def azure_create_container(container):
    try:
        print(f"Creating container: {container}")
        blob_service_client = azure_get_blob_service_client()
        container_client = blob_service_client.get_container_client(container)
        container_client.create_container()
        properties = container_client.get_container_properties()
        print(f"----------- properties of new container {container} --------------")
        print(properties)
        print("-------------------------------------------------------------------")
    except Exception as ex:
        print(ex)


def azure_get_containers(prefix):
    blob_service_client = azure_get_blob_service_client()
    containers = blob_service_client.list_containers(name_starts_with=prefix)
    return containers


def azure_delete_dir(container, prefix):
    client = DirectoryClient(AZURE_STORAGE_CONNECTION_STRING, container)
    client.rmdir(prefix)


def azure_download(container, source, dest):
    client = DirectoryClient(AZURE_STORAGE_CONNECTION_STRING, container)
    client.download(source, dest)


# TODO: needs some integration with guessing mimetypes
# def azure_upload(container, source, dest):
#     client = DirectoryClient(AZURE_STORAGE_CONNECTION_STRING, container)
#     client.upload(source, dest)


def azure_upload_dir(local_directory, container):
    try:
        blob_service_client = azure_get_blob_service_client()
        container_client = blob_service_client.get_container_client(container)

        for root, dirs, files in os.walk(local_directory):

            for filename in files:
                # construct the full local path
                local_path = os.path.join(root, filename)
                mimetype = guess_mimetype(local_path)

                # construct the full Dropbox path
                relative_path = os.path.relpath(local_path, local_directory)

                # Upload the file
                print("Uploading:\t" + relative_path)
                content_settings = ContentSettings(content_type=mimetype)
                with open(local_path, "rb") as data:
                    container_client.upload_blob(
                        name=relative_path, data=data, content_settings=content_settings
                    )

    except Exception as ex:
        print(ex)


def guess_mimetype(local_file, default_mimetype="binary/octet-stream"):
    """

    :param local_file:
    :param default_mimetype:
    :return: String

    https://gist.github.com/feelinc/d1f541af4f31d09a2ec3
    """
    mimetype, _ = mimetypes.guess_type(local_file)

    # wouldn't be needed if this is resolved
    # https://bugs.python.org/issue39324
    if not mimetype and str(local_file).endswith(".md"):
        mimetype = "text/markdown"

    if not mimetype:
        mimetype = default_mimetype
        # print(f"Failed to guess mimetype for {local_file}. Setting to {mimetype}")
    return mimetype


def do_delete_dir(destination):
    # enumerate local files recursively
    s3 = boto3.resource(
        "s3",
        region_name="nyc3",
        endpoint_url="https://nyc3.digitaloceanspaces.com",
        aws_access_key_id=DO_ACCESS_KEY_ID,
        aws_secret_access_key=DO_SECRET_ACCESS_KEY,
    )
    bucket = s3.Bucket(DO_SPACE)
    bucket.objects.filter(Prefix=destination).delete()


def do_download_dir(client, bucket, remote_folder, local_folder):
    """
    params:
    - client: initialized s3 client object
    - bucket: s3 bucket with target contents
    - remote_folder: pattern to match in s3
    - local_folder: local path to folder in which to place files

    not used now, but could be useful to download the whole _build directory from the Travis CI build to test
    https://stackoverflow.com/a/56267603
    """
    keys = []
    dirs = []
    next_token = ""
    base_kwargs = {
        "Bucket": bucket,
        "Prefix": remote_folder,
    }
    while next_token is not None:
        kwargs = base_kwargs.copy()
        if next_token != "":
            kwargs.update({"ContinuationToken": next_token})
        results = client.list_objects_v2(**kwargs)
        contents = results.get("Contents")
        for i in contents:
            k = i.get("Key")
            if k[-1] != "/":
                keys.append(k)
            else:
                dirs.append(k)
        next_token = results.get("NextContinuationToken")

    for d in dirs:
        dest_pathname = os.path.join(local_folder, d)
        if not os.path.exists(os.path.dirname(dest_pathname)):
            os.makedirs(os.path.dirname(dest_pathname))

    for k in keys:
        dest_pathname = os.path.join(local_folder, k)
        if not os.path.exists(os.path.dirname(dest_pathname)):
            os.makedirs(os.path.dirname(dest_pathname))
        client.download_file(bucket, k, dest_pathname)


def do_download_file(remote_file, local_file, force=False):
    """
    Used in Travis CI to download and unzip the file of original artwork from Digitalocean Spaces.
    Once run, they should be unzipped so that there is a top level directory called albums.

    The structure of the folder is such:

    albums/
    |--- dmg/
    |    |--- dmg_bottom/
    |    |    |--- 0001.png
    |    |    |--- 000x.png
    |    |    |--- index.md
    |    |--- dmg_xxxx/
    |    |--- index.md
    |--- maybe-later/
    |--- phb/
    |--- templates/
    |--- index.md
    """
    session = Session()

    client = session.client(
        "s3",
        region_name="nyc3",
        endpoint_url="https://nyc3.digitaloceanspaces.com",
        aws_access_key_id=DO_ACCESS_KEY_ID,
        aws_secret_access_key=DO_SECRET_ACCESS_KEY,
    )

    file = Path(local_file)
    if not file.exists():
        print(f"Downloading: {remote_file}")
    elif force:
        print(f"Forcing download, overwriting {local_file}")
    else:
        print(f"{local_file} already downloaded, using local copy")
        return
    client.download_file(DO_SPACE, remote_file, local_file)


def do_upload_dir(local_directory, destination):
    """

    :param local_directory:
    :param destination:
    :return:
    """
    # Digitalocean Spaces
    bucket = DO_SPACE
    session = Session()
    client = session.client(
        "s3",
        region_name="nyc3",
        endpoint_url="https://nyc3.digitaloceanspaces.com",
        aws_access_key_id=DO_ACCESS_KEY_ID,
        aws_secret_access_key=DO_SECRET_ACCESS_KEY,
    )
    # enumerate local files recursively
    for root, dirs, files in os.walk(local_directory):

        for filename in files:

            # construct the full local path
            local_path = os.path.join(root, filename)
            mimetype = guess_mimetype(local_path)

            # construct the full Dropbox path
            relative_path = os.path.relpath(local_path, local_directory)
            s3_path = os.path.join(destination, relative_path)

            # relative_path = os.path.relpath(os.path.join(root, filename))
            # print(f"Searching {s3_path} in {bucket}")
            try:
                client.head_object(Bucket=bucket, Key=s3_path)
                print(f"Path found on S3! Skipping {s3_path}...")

                # try:
                #     client.delete_object(Bucket=bucket, Key=s3_path)
                # except:
                #     print(f"Unable to delete {s3_path}...")
            except:
                print(f"Uploading {s3_path}...")
                client.upload_file(
                    local_path,
                    bucket,
                    s3_path,
                    ExtraArgs={"ACL": "public-read", "ContentType": mimetype},
                )


def do_upload_file(archive_file, upload_location):
    """

    :param archive_file:
    :param upload_location:
    :return:
    """
    session = Session()

    client = session.client(
        "s3",
        region_name="nyc3",
        endpoint_url="https://nyc3.digitaloceanspaces.com",
        aws_access_key_id=DO_ACCESS_KEY_ID,
        aws_secret_access_key=DO_SECRET_ACCESS_KEY,
    )

    client.upload_file(archive_file, DO_SPACE, upload_location)


def unzip_file(filename):
    with zipfile.ZipFile(filename, "r") as zip_ref:
        print(f"Extracting {filename}. Should create a top level `albums` directory.")
        zip_ref.extractall()


def zipdir(dir_to_zip, archive_file):
    """

    :param dir_to_zip:
    :param archive_file:
    :return:

    https://stackoverflow.com/a/1855118
    """
    with zipfile.ZipFile(archive_file, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(dir_to_zip):
            for file in files:
                zipf.write(os.path.join(root, file))


def remove_empty_folders(path, remove_root=True):
    """Function to remove empty folders."""
    if not os.path.isdir(path):
        return

    # remove empty subfolders
    files = os.listdir(path)
    if len(files):
        for f in files:
            fullpath = os.path.join(path, f)
            if os.path.isdir(fullpath):
                remove_empty_folders(fullpath)

    # if folder empty, delete it
    files = os.listdir(path)
    if len(files) == 0 and remove_root:
        # print("Removing empty folder:", path)
        os.rmdir(path)
