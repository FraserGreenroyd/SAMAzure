import datetime
import azure.storage.blob as azureblob
import azure.batch.models as batchmodels

import argparse

# ************************************************** #
# ***   Public methods                           *** #
# ************************************************** #

def create_container(block_blob_client, container_name):

    print("Creating container [{0:}]".format(container_name))

    return block_blob_client.create_container(container_name, fail_on_exist=False)

def upload_file_to_container(block_blob_client, container_name, file_path):
    """
    Uploads a local file to an Azure Blob storage container.

    :param block_blob_client: A blob service client.
    :type block_blob_client: `azure.storage.blob.BlockBlobService`
    :param str container_name: The name of the Azure Blob storage container.
    :param str file_path: The local path to the file.
    :rtype: `azure.batch.models.ResourceFile`
    :return: A ResourceFile initialized with a SAS URL appropriate for Batch
    tasks.
    """

    blob_name = os.path.basename(file_path)

    print('Uploading file {} to container [{}]'.format(blob_name, container_name))

    block_blob_client.create_blob_from_path(container_name, blob_name, file_path)

    sas_token = block_blob_client.generate_blob_shared_access_signature(container_name, blob_name, permission=azureblob.BlobPermissions.READ, expiry=datetime.datetime.utcnow() + datetime.timedelta(hours=24))

    sas_url = block_blob_client.make_blob_url(container_name, blob_name, sas_token=sas_token)

    return batchmodels.ResourceFile(file_path=blob_name, blob_source=sas_url)

def get_container_sas_token(block_blob_client, container_name, blob_permissions):
    """
    Obtains a shared access signature granting the specified permissions to the container.

    :param block_blob_client: A blob service client.
    :type block_blob_client: `azure.storage.blob.BlockBlobService`
    :param str container_name: The name of the Azure Blob storage container.
    :param BlobPermissions blob_permissions:
    :rtype: str
    :return: A SAS token granting the specified permissions to the container.
    """
    # Obtain the SAS token for the container, setting the expiry time and permissions. In this case, no start time is specified, so the shared access signature becomes valid immediately.
    container_sas_token = \
        block_blob_client.generate_container_shared_access_signature(
            container_name,
            permission=blob_permissions,
            expiry=datetime.datetime.utcnow() + datetime.timedelta(hours=24))

    return container_sas_token

# ************************************************** #
# ***   Main execution                           *** #
# ************************************************** #
if __name__ == "__main__":

    _BATCH_ACCOUNT_NAME = "climatebasedbatch"
    _BATCH_ACCOUNT_KEY = "W94ukoxG2neFkk6teOVZ3IQ8IQjmPJqPcFq48I9lLzCrPEQSRFS/+euaUEkkSyPoulUgnx5IEZxztA9574Hluw=="
    _BATCH_ACCOUNT_URL = "https://climatebasedbatch.westeurope.batch.azure.com"

    _STORAGE_ACCOUNT_NAME = "radfiles"
    _STORAGE_ACCOUNT_KEY = "aRRVzOkO/kwS35CIwNVIa18aGoMfZD5D3yAy3GlorkkU2G+9q5rAscXoC21IIylJZerBefwMgxYYF3qzquALrw=="

    _POOL_ID = "1st_deployment"
    _MIN_POOL_NODE = 1
    _MAX_POOL_NODE = 100

    _POOL_VM_SIZE = "BASIC_A1"
    _NODE_OS_PUBLISHER = "Canonical"
    _NODE_OS_OFFER = "UbuntuServer"
    _NODE_OS_SKU = "16"

    # _CONTAINER = "0000000-jobs-3513"

    parser = argparse.ArgumentParser(description="Run Azure batch daylight analysis")
    parser.add_argument("-p", "--analysisPoints", help="Path to the JSON analysis grid points to simulate")
    parser.add_argument("-c", "--container", help="Container in which to store files for task/job")
    parser.add_argument("-sm", "--skyMatrix", help="Path to the sky matrix")
    parser.add_argument("-s", "--surfaces", help="Path to the context opaque and transparent surfaces")
    parser.add_argument("-q", "--quality", type=str, help="Optional simulation quality ['low', 'medium', 'high']. Default is 'low'")
    args = parser.parse_args()

    analysis_grid_path = args.analysisPoints
    surfaces_path = args.surfaces
    sky_matrix_path = args.skyMatrix




    # ************************************************* #

    # Create the Blob client
    blob_client = azureblob.BlockBlobService(account_name=_STORAGE_ACCOUNT_NAME, account_key=_STORAGE_ACCOUNT_KEY)

    # Create container to hold files
    create_container(blob_client, _CONTAINER)

    # Upload file/s to blob
    file_s = r"C:\Users\tgerrish\Documents\GitHub\BHoM\.gitignore"
    upload_file_to_container(blob_client, _CONTAINER, file_s)

    # Get sas token
    sas_token = get_container_sas_token(blob_client, _CONTAINER, azureblob.BlobPermissions.WRITE)

    # Create the Batch client
    credentials = batchauth.SharedKeyCredentials(_BATCH_ACCOUNT_NAME, _BATCH_ACCOUNT_KEY)
    batch_client = batch.BatchServiceClient(credentials, base_url=_BATCH_ACCOUNT_URL)