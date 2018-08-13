import argparse
import json

import datetime
import shutil
import os
import azure.storage.blob as azureblob
import azure.batch.models as batchmodels

import time

# ************************************************** #
# ***   Public methods                           *** #
# ************************************************** #

def load_json(path):
    """
    Load a JSON file into a dictionary object
    :type path: Path to JSON file
    :return: Dictionary representing content of JSON file
    """
    with open(path) as data_file:
        return json.load(data_file)

# ************************************************** #
# ***   Main execution                           *** #
# ************************************************** #

patience = 10

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Uploads a local file or directory of files and sub-directories to an Azure Blob storage container")
    parser.add_argument("-o", "--object", help="Single file or directory object")
    parser.add_argument("-c", "--credentials", help="Azure credentials file")
    parser.add_argument("-t", "--target", help="Blob resource container name")
    args = parser.parse_args()

    objects = args.object
    credentials = load_json(str(args.credentials))
    blob_resource_container = args.target

    storage_account_name = credentials["_STORAGE_ACCOUNT_NAME"]
    storage_account_key = credentials["_STORAGE_ACCOUNT_KEY"]

    # Generate the blob-client about which all transactions are associated
    blob_client = azureblob.BlockBlobService(account_name=storage_account_name, account_key=storage_account_key)

    # Create resources blob location
    blob_client.create_container(blob_resource_container, fail_on_exist=False)
    print("\nWaiting for {0:} seconds - letting Azure create the container before uploading files".format(patience))
    for t in reversed(range(patience)):
        print("{0:}".format(t+1))
        time.sleep(1)

    print("Uploading ...")
    if os.path.isfile(objects):
        blob_client.create_blob_from_path(blob_resource_container, os.path.basename(objects), objects, timeout=5, max_connections=4)
        print("Container [{1:}/{0:}] created from {2:}".format(os.path.basename(objects), blob_resource_container, objects))
    elif os.path.isdir(objects):
        # Get the paths to all files in the selected directory
        paths = []
        for root, dirs, files in os.walk(os.path.abspath(objects)):
            for file in files:
                paths.append(os.path.os.path.join(root, file))
        # Obtain the common prefix to each file
        # common_prefix = os.path.commonprefix(paths)
        # For each file, upload to the target blob in the same structure
        nm = objects.split("\\")[-1]
        for file in paths:
            print("Container [{2:}\\{1:}] created from {0:}".format(file, os.path.normpath("{0:}\\{1:}".format(nm, file.replace(objects, ""))), blob_resource_container))
            blob_client.create_blob_from_path(blob_resource_container, os.path.normpath("{0:}\\{1:}".format(nm, file.replace(objects, ""))), file, timeout=5, max_connections=4)

    print("\nUpload sucessful!")