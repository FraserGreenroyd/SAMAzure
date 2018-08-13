import azure.storage.blob as azureblob
import argparse
import os
import json

# # ************************************************** #
# # ***   Public methods                           *** #
# # ************************************************** #

def load_json(path):
    """
    Load a JSON file into a dictionary object

    :type path: Path to JSON file
    :return: Dictionary representing content of JSON file
    """
    with open(path) as data_file:
        return json.load(data_file)

def download_blobs_from_container(block_blob_client, container_name, directory_path):
    """
    Downloads all blobs from the specified Azure Blob storage container.

    :param block_blob_client: A blob service client.
    :type block_blob_client: `azure.storage.blob.BlockBlobService`
    :param container_name: The Azure Blob storage container from which to
     download files.
    :param directory_path: The local directory to which to download the files.
    """
    print('Downloading all files from container [{}]...'.format(
        container_name))

    container_blobs = block_blob_client.list_blobs(container_name)

    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

    for blob in container_blobs.items:
        destination_file_path = os.path.join(directory_path, blob.name)
        if not os.path.exists(os.path.dirname(destination_file_path)):
            os.makedirs(os.path.dirname(destination_file_path))

        block_blob_client.get_blob_to_path(container_name,
                                           blob.name,
                                           destination_file_path)

        print('  Downloaded blob [{}] from container [{}] to {}'.format(
            blob.name,
            container_name,
            destination_file_path))

    print('  Download complete!')


# # ************************************************** #
# # ***   Main execution                           *** #
# # ************************************************** #


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Downloads an entire Azure Blob storage container")
    parser.add_argument("-n", "--container", help="Container name")
    parser.add_argument("-c", "--credentials", help="Azure credentials file")
    parser.add_argument("-d", "--directory", help="Target save directory")
    args = parser.parse_args()

    blob_resource_container = args.container
    target_dir = args.directory
    credentials = load_json(str(args.credentials))

    storage_account_name = credentials["_STORAGE_ACCOUNT_NAME"]
    storage_account_key = credentials["_STORAGE_ACCOUNT_KEY"]

    # Generate the blob-client about which all transactions are associated
    blob_client = azureblob.BlockBlobService(account_name=storage_account_name, account_key=storage_account_key)

    download_blobs_from_container(blob_client, blob_resource_container, target_dir)