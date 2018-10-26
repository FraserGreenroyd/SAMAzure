import configparser
import argparse
import datetime
import os
import uuid
import sys
import re

import azure.storage.blob as azureblob
import azure.batch.batch_service_client as batch
import azure.batch.batch_auth as batchauth
import azure.batch.models as batchmodels


if sys.version_info[0] < 3:
    raise Exception("Must be using Python 3+")


def find_files(directory, extension):
    """Lists files of a specified extension in the target directory.

    :param str directory: The directory to explore.
    :param str extension: The file extension to search for.
    :return str: List of files with extension found
    """
    files = []
    for file in os.listdir(directory):
        if file.endswith(extension):
            files.append(os.path.abspath(os.path.join(directory, file)))
    return sorted(files)


def get_case_files(case_directory):
    """Gets the Radiance case files to be uploaded and processed.

    :param str case_directory: The case directory from which files will be grabbed.
    :return (str, str, [str]): Sky matrix, Surfaces, Analysis Grid/s
    """
    sky_matrix = os.path.join(case_directory, "sky_mtx.json")
    surfaces = os.path.join(case_directory, "surfaces.json")
    grids = find_files(os.path.join(case_directory, "AnalysisGrids"), ".json")

    return sky_matrix, surfaces, grids


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

    print('[{1:}] < {0:}'.format(os.path.relpath(file_path), container_name))

    block_blob_client.create_blob_from_path(container_name, blob_name, file_path)

    # Obtain the SAS token for the container.
    sas_token = get_container_sas_token(block_blob_client, container_name, azureblob.BlobPermissions.READ)

    sas_url = block_blob_client.make_blob_url(container_name, blob_name, sas_token=sas_token)

    return batchmodels.ResourceFile(file_path=blob_name, blob_source=sas_url)


def wrap_commands_in_shell(ostype, commands):
    """
    Wrap commands in a shell

    :param list commands: list of commands to wrap
    :param str ostype: OS type, linux or windows
    :rtype: str
    :return: a shell wrapping commands
    """
    if ostype.lower() == "linux":
        return "/bin/bash -c \"set -e; set -o pipefail; {0:}; wait\"".format(";".join(commands))
    elif ostype.lower() == "windows":
        return "cmd.exe /c {0:}".format("&".join(commands))
    else:
        raise ValueError("unknown ostype: {}".format(ostype))


def select_latest_verified_vm_image_with_node_agent_sku(batch_client, publisher, offer, sku_starts_with):
    """Select the latest verified image that Azure Batch supports given
    a publisher, offer and sku (starts with filter).

    :param batch_client: The batch client to use.
    :type batch_client: `batchserviceclient.BatchServiceClient`
    :param str publisher: vm image publisher
    :param str offer: vm image offer
    :param str sku_starts_with: vm sku starts with filter
    :rtype: tuple
    :return: (node agent sku id to use, vm image ref to use)
    """
    # get verified vm image list and node agent sku ids from service
    node_agent_skus = batch_client.account.list_node_agent_skus()
    # pick the latest supported sku
    skus_to_use = [
        (sku, image_ref) for sku in node_agent_skus for image_ref in sorted(
            sku.verified_image_references, key=lambda item: item.sku)
        if image_ref.publisher.lower() == publisher.lower() and
           image_ref.offer.lower() == offer.lower() and
           image_ref.sku.startswith(sku_starts_with)
    ]
    # skus are listed in reverse order, pick first for latest
    sku_to_use, image_ref_to_use = skus_to_use[0]
    return (sku_to_use.id, image_ref_to_use)


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
    # Obtain the SAS token for the container, setting the expiry time and permissions. In this case, no start time is specified, so the shared access signature becomes valid immediately. Expiration is in 2 hours.
    container_sas_token = block_blob_client.generate_container_shared_access_signature(container_name, permission=blob_permissions, expiry=datetime.datetime.utcnow() + datetime.timedelta(hours=2))

    return container_sas_token


def get_container_sas_url(block_blob_client, container_name):
    """
    Obtains a shared access signature URL that provides access to the ouput container to which the tasks will upload their output.

    :param block_blob_client: A blob service client.
    :type block_blob_client: `azure.storage.blob.BlockBlobService`
    :param str container_name: The name of the Azure Blob storage container.
    :rtype: str
    :return: A SAS URL granting the specified permissions to the container.
    """
    # Obtain the SAS token for the container.
    sas_token = get_container_sas_token(block_blob_client, container_name, azureblob.BlobPermissions(read=True, write=True))

    # Construct SAS URL for the container
    container_sas_url = "https://{}.blob.core.windows.net/{}?{}".format(_STORAGE_ACCOUNT_NAME, container_name, sas_token)

    return container_sas_url


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Send job to Azure")

    parser.add_argument(
        "-d",
        "--caseDirectory",
        type=str,
        help="Path to the case directory from which simulation ingredients are obtained",
        default="./case")  # TODO - Remove post testing
    parser.add_argument(
        "-c",
        "--configFile",
        type=str,
        help="Path to the azure config file",
        default="./azure_configuration.cfg")  # TODO - Remove post testing
    parser.add_argument(
        "-j",
        "--jobID",
        type=str,
        help="ID for the job being undertaken",
        default="0000000-testjob-3513")  # TODO - Remove post testing

    args = parser.parse_args()

    _CASE_DIRECTORY = args.caseDirectory
    _JOB_ID = args.jobID
    _CONFIG_FILE = args.configFile

    global_config = configparser.RawConfigParser()
    global_config.read(_CONFIG_FILE)

    _BATCH_ACCOUNT_NAME = global_config.get("Batch", "batchaccountname")
    _BATCH_ACCOUNT_KEY = global_config.get("Batch", "batchaccountkey")
    _BATCH_ACCOUNT_URL = global_config.get("Batch", "batchserviceurl")
    _STORAGE_ACCOUNT_NAME = global_config.get("Storage", "storageaccountname")
    _STORAGE_ACCOUNT_KEY = global_config.get("Storage", "storageaccountkey")
    _STORAGE_ACCOUNT_SUFFIX = global_config.get("Storage", "storageaccountsuffix")
    _POOL_ID = global_config.get("Default", "poolid")
    _POOL_VM_SIZE = global_config.get("Default", "poolvmsize")
    _MIN_POOL_NODE = global_config.getint("Default", "poolvmcountmin")
    _MAX_POOL_NODE = global_config.getint("Default", "poolvmcountmax")
    _NODE_OS_PUBLISHER = global_config.get("Default", "nodepublisher")
    _NODE_OS_OFFER = global_config.get("Default", "nodeoffer")
    _NODE_OS_SKU = global_config.get("Default", "nodesku")

    _RADIANCE_SAS_TOKEN = global_config.get("Process", "radiancesastoken")
    _RADIANCE_SAS_URL = global_config.get("Process", "radiancesasurl")
    _LB_HB_SAS_TOKEN = global_config.get("Process", "lbhbsastoken")
    _LB_HB_SAS_URL = global_config.get("Process", "lbhbsasurl")
    _SCRIPT_SAS_TOKEN = global_config.get("Process", "scriptsastoken")
    _SCRIPT_SAS_URL = global_config.get("Process", "scriptsasurl")
    _COPYTOBLOB_SAS_TOKEN = global_config.get("Process", "copytoblobsastoken")
    _COPYTOBLOB_SAS_URL = global_config.get("Process", "copytoblobsasurl")

    _DELETE_CONTAINER = global_config.getboolean("Default", "shoulddeletecontainer")
    _DELETE_JOB = global_config.getboolean("Default", "shoulddeletejob")
    _DELETE_POOL = global_config.getboolean("Default", "shoulddeletepool")

    # File accessibility expiry time
    expiry = datetime.datetime.utcnow() + datetime.timedelta(minutes=global_config.getint("Default", "blobreadtimeout"))

    # Create the blob client
    blob_client = azureblob.BlockBlobService(account_name=_STORAGE_ACCOUNT_NAME, account_key=_STORAGE_ACCOUNT_KEY)

    # Create a job container
    blob_client.create_container(_JOB_ID, fail_on_exist=False)
    container_sas_token = blob_client.generate_container_shared_access_signature(
        _JOB_ID,
        permission=azureblob.BlobPermissions(read=True, write=True),
        expiry=expiry)
    output_container_sas_url = "https://{0:}.blob.core.windows.net/{1:}?{2:}".format(_STORAGE_ACCOUNT_NAME, _JOB_ID, container_sas_token)
    print('[{0:}] container created.'.format(_JOB_ID))

    # Upload case files to job container
    _SKY_MTX_FILEPATH, _SURFACES_FILEPATH, _ANALYSIS_GRIDS_FILEPATHS = get_case_files(_CASE_DIRECTORY)
    surfaces_file = upload_file_to_container(blob_client, _JOB_ID, _SURFACES_FILEPATH)
    sky_mtx_file = upload_file_to_container(blob_client, _JOB_ID, _SKY_MTX_FILEPATH)
    analysis_grid_files = [upload_file_to_container(blob_client, _JOB_ID, file_path) for file_path in _ANALYSIS_GRIDS_FILEPATHS]

    # Generate batch credentials and client
    batch_credentials = batchauth.SharedKeyCredentials(_BATCH_ACCOUNT_NAME, _BATCH_ACCOUNT_KEY)
    batch_client = batch.BatchServiceClient(batch_credentials, base_url=_BATCH_ACCOUNT_URL)




    #
    # # Get the node agent SKU and image reference for the virtual machine configuration.
    # sku_to_use, image_ref_to_use = select_latest_verified_vm_image_with_node_agent_sku(batch_client, _NODE_OS_PUBLISHER, _NODE_OS_OFFER, _NODE_OS_SKU)
    #
    # # Specify the user permissions and level
    # user = batchmodels.AutoUserSpecification(scope=batchmodels.AutoUserScope.pool, elevation_level=batchmodels.ElevationLevel.admin)
    #
    # # Define the start task for the pool
    # start_task = batch.models.StartTask(
    #     command_line=wrap_commands_in_shell("linux", start_commands),
    #     user_identity=batchmodels.UserIdentity(auto_user=user),
    #     wait_for_success=True,
    #     resource_files=resources
    # )
    #
    # # Define the pool
    # new_pool = batch.models.PoolAddParameter(
    #     id=_POOL_ID,
    #     virtual_machine_configuration=batchmodels.VirtualMachineConfiguration(
    #         image_reference=image_ref_to_use,
    #         node_agent_sku_id=sku_to_use
    #     ),
    #     vm_size=_POOL_VM_SIZE,
    #     enable_auto_scale=True,
    #     auto_scale_formula='pendingTaskSamplePercent =$PendingTasks.GetSamplePercent(180 * TimeInterval_Second);pendingTaskSamples = pendingTaskSamplePercent < 70 ? 1 : avg($PendingTasks.GetSample(180 * TimeInterval_Second)); $TargetDedicatedNodes = min(100, pendingTaskSamples);',
    #     auto_scale_evaluation_interval=datetime.timedelta(minutes=5),
    #     start_task=start_task,
    # )
    #
    # # Try to create the pool, and tell us why not
    # try:
    #     batch_client.pool.add(new_pool)
    # except batchmodels.batch_error.BatchErrorException as err:
    #     print_batch_exception(err)
    #     raise
    #
    # print('[{0:}] pool created'.format(_POOL_ID))
    #
    #
    #
    #
    #
    #
    # # Create a pool
    # # Get the node agent SKU and image reference for the virtual machine configuration.
    # sku_to_use, image_ref_to_use = select_latest_verified_vm_image_with_node_agent_sku(batch_client, _NODE_OS_PUBLISHER, _NODE_OS_OFFER, _NODE_OS_SKU)
    #
    # # Specify the user permissions and level
    # user = batchmodels.AutoUserSpecification(scope=batchmodels.AutoUserScope.pool, elevation_level=batchmodels.ElevationLevel.admin)
    #
    # # Define the start task for the pool
    # start_task = batch.models.StartTask(
    #     command_line=wrap_commands_in_shell("linux", ["sudo touch ./do_i_exist.txt", "sudo cp -p do_i_exist.txt $AZ_BATCH_NODE_SHARED_DIR"]),
    #     user_identity=batchmodels.UserIdentity(auto_user=user),
    #     wait_for_success=True,
    #     resource_files=[]
    # )
    #
    # # Create a job
    # batch_client.job.add(job=_JOB_ID)
    # print('[{}] job created...'.format(_JOB_ID))
    #
    #
    #
    #
    #
    # # Create a bunch of tasks
    # tasks = []
    # for n, grid_file in enumerate(analysis_grid_files):
    #     task_id = 'task_{0:}'.format(re.sub("[^0-9a-zA-Z]", "", grid_file.file_path.replace(".json", "")))
    #
    #     resource_files = [
    #         batchmodels.ResourceFile(file_path="radiance-5.1.0-Linux.tar.gz", blob_source=_RADIANCE_SAS_URL),
    #         batchmodels.ResourceFile(file_path="lb_hb.tar.gz", blob_source=_LB_HB_SAS_URL),
    #         batchmodels.ResourceFile(file_path="RunHoneybeeRadiance.py", blob_source=_SCRIPT_SAS_URL),
    #         batchmodels.ResourceFile(file_path="copy_to_blob.py", blob_source=_COPYTOBLOB_SAS_URL),
    #         surfaces_file,
    #         sky_mtx_file,
    #         grid_file,
    #     ]
    #
    #     task_commands = [
    #         # Move to the BEST directory!
    #         "cd",
    #         "cd /",
    #         # Set up radiance software
    #         "sudo cp -p radiance-5.1.0-Linux.tar.gz $AZ_BATCH_NODE_SHARED_DIR",
    #         "sudo tar xzf radiance-5.1.0-Linux.tar.gz",
    #         "sudo rsync -av /radiance-5.1.0-Linux/usr/local/radiance/bin/ /usr/local/bin/",
    #         "sudo rsync -av /radiance-5.1.0-Linux/usr/local/radiance/lib/ /usr/local/lib/ray/",
    #         # Set up Ladybug tools
    #         "sudo cp -p lb_hb.tar.gz $AZ_BATCH_NODE_SHARED_DIR",
    #         "sudo tar xzf lb_hb.tar.gz",
    #         # Get the script and files to be run
    #         "sudo cp -p RunHoneybeeRadiance.py $AZ_BATCH_NODE_SHARED_DIR",
    #         "sudo cp -p copy_to_blob.py $AZ_BATCH_NODE_SHARED_DIR",
    #         "sudo cp -p surfaces.json $AZ_BATCH_NODE_SHARED_DIR",
    #         "sudo cp -p sky_mtx.json $AZ_BATCH_NODE_SHARED_DIR",
    #         "sudo cp -p {0:} $AZ_BATCH_NODE_SHARED_DIR".format(grid_file.file_path),
    #         # Run the simulation
    #         "sudo python ./RunHoneybeeRadiance.py -s ./surfaces.json -sm ./sky_mtx.json -p ./{0:}".format(grid_file.file_path),
    #         # Copy the results back to the blob
    #         "sudo python copy_to_blob.py -fp {0:} -bn {1:} -sa {2:} -sc {0:} -st {3:}".format(
    #             grid_file.file_path.replace(".json", "_results.json"),
    #             _JOB_ID,
    #             _STORAGE_ACCOUNT_NAME,
    #             _STORAGE_ACCOUNT_KEY
    #         )
    #     ]
    #
    #     bash_commands = wrap_commands_in_shell("linux", task_commands)
    #
    #     tasks.append(
    #         batchmodels.TaskAddParameter(
    #             id=task_id,
    #             display_name=task_id,
    #             command_line=bash_commands,
    #             resource_files=resource_files,
    #             output_files=[
    #                 batchmodels.OutputFile(
    #                     file_pattern="*_result.json",
    #                     # container=_JOB_ID,
    #                     # container_url="https://{0:}.blob.core.windows.net/{1:}".format(_STORAGE_ACCOUNT_NAME, _JOB_ID),
    #                     destination=batchmodels.OutputFileDestination(container=batchmodels.OutputFileBlobContainerDestination(container_url=output_container_sas_url)),
    #                     upload_options=batchmodels.OutputFileUploadOptions(upload_condition=batchmodels.OutputFileUploadCondition.task_success)
    #                 )
    #             ]
    #         )
    #     )
    #
    # # Add tasks to the batch client
    # for i in tasks:
    #     batch_client.task.add(job_id=_JOB_ID, task=i)
    #
    # print(tasks)


