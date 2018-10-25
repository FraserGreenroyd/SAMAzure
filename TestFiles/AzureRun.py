import sys
if sys.version_info[0] < 3:
    raise Exception("Must be using Python 3+")


import datetime
import io
import os
import re
import sys
import time
import unicodedata

import azure.storage.blob as azureblob
import azure.batch.batch_service_client as batch
import azure.batch.batch_auth as batchauth
import azure.batch.models as batchmodels


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


def query_yes_no(question, default="yes"):
    """
    Prompts the user for yes/no input, displaying the specified question text.

    :param str question: The text of the prompt for input.
    :param str default: The default if the user hits <ENTER>. Acceptable values are 'yes', 'no', and None.
    :rtype: str
    :return: 'yes' or 'no'
    """
    valid = {'y': 'yes', 'n': 'no'}
    if default is None:
        prompt = ' [y/n] '
    elif default == 'yes':
        prompt = ' [Y/n] '
    elif default == 'no':
        prompt = ' [y/N] '
    else:
        raise ValueError("Invalid default answer: '{}'".format(default))

    while 1:
        choice = input(question + prompt).lower()
        if default and not choice:
            return default
        try:
            return valid[choice[0]]
        except (KeyError, IndexError):
            print("Please respond with 'yes' or 'no' (or 'y' or 'n').\n")


def print_batch_exception(batch_exception):
    """
    Prints the contents of the specified Batch exception.

    :param batch_exception:
    """
    print('-------------------------------------------')
    print('Exception encountered:')
    if batch_exception.error and batch_exception.error.message and batch_exception.error.message.value:
        print(batch_exception.error.message.value)
        if batch_exception.error.values:
            print()
            for mesg in batch_exception.error.values:
                print('{}:\t{}'.format(mesg.key, mesg.value))
    print('-------------------------------------------')


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

    print('Uploading file {} to [{}]...'.format(file_path, container_name))

    block_blob_client.create_blob_from_path(container_name, blob_name, file_path)

    # Obtain the SAS token for the container.
    sas_token = get_container_sas_token(block_blob_client, container_name, azureblob.BlobPermissions.READ)

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
    # Obtain the SAS token for the container, setting the expiry time and permissions. In this case, no start time is specified, so the shared access signature becomes valid immediately. Expiration is in 2 hours.
    container_sas_token = block_blob_client.generate_container_shared_access_signature(
        container_name,
        permission=blob_permissions,
        expiry=datetime.datetime.utcnow() + datetime.timedelta(hours=2)
    )

    return container_sas_token


def get_container_sas_url(block_blob_client, container_name, blob_permissions):
    """
    Obtains a shared access signature URL that provides write access to the ouput container to which the tasks will upload their output.

    :param block_blob_client: A blob service client.
    :type block_blob_client: `azure.storage.blob.BlockBlobService`
    :param str container_name: The name of the Azure Blob storage container.
    :param BlobPermissions blob_permissions:
    :rtype: str
    :return: A SAS URL granting the specified permissions to the container.
    """
    # Obtain the SAS token for the container.
    sas_token = get_container_sas_token(block_blob_client, container_name, azureblob.BlobPermissions.WRITE)

    # Construct SAS URL for the container
    container_sas_url = "https://{}.blob.core.windows.net/{}?{}".format(_STORAGE_ACCOUNT_NAME, container_name,
                                                                        sas_token)

    return container_sas_url


def wait_for_tasks_to_complete(batch_service_client, job_id, timeout):
    """
    Returns when all tasks in the specified job reach the Completed state.

    :param batch_service_client: A Batch service client.
    :type batch_service_client: `azure.batch.BatchServiceClient`
    :param str job_id: The id of the job whose tasks should be monitored.
    :param timedelta timeout: The duration to wait for task completion. If all tasks in the specified job do not reach Completed state within this time period, an exception will be raised.
    """
    timeout_expiration = datetime.datetime.now() + timeout

    print("Monitoring all tasks for 'Completed' state, timeout in {}...".format(timeout), end='')

    while datetime.datetime.now() < timeout_expiration:
        print('.', end='')
        sys.stdout.flush()
        tasks = batch_service_client.task.list(job_id)
        incomplete_tasks = [task for task in tasks if task.state != batchmodels.TaskState.completed]
        if not incomplete_tasks:
            print()
            return True
        else:
            time.sleep(1)

    print()
    raise RuntimeError("ERROR: Tasks did not reach 'Completed' state within timeout period of " + str(timeout))


# TODO - Remove hardcoded things!!!

# GLOBAL
_BATCH_ACCOUNT_NAME = "climatebasedbatch"
_BATCH_ACCOUNT_KEY = "W94ukoxG2neFkk6teOVZ3IQ8IQjmPJqPcFq48I9lLzCrPEQSRFS/+euaUEkkSyPoulUgnx5IEZxztA9574Hluw=="
_BATCH_ACCOUNT_URL = "https://climatebasedbatch.westeurope.batch.azure.com"

_STORAGE_ACCOUNT_NAME = "radfiles"
_STORAGE_ACCOUNT_KEY = "aRRVzOkO/kwS35CIwNVIa18aGoMfZD5D3yAy3GlorkkU2G+9q5rAscXoC21IIylJZerBefwMgxYYF3qzquALrw=="

_POOL_ID = 'radbatchpool'
_DEDICATED_POOL_NODE_COUNT = 0
_LOW_PRIORITY_POOL_NODE_COUNT = 2 # TODO - Add autosize function - prevent having to manually specify number of nodes to spin up!
_POOL_VM_SIZE = 'STANDARD_A1_v2'
_JOB_ID = 'radbatchjob'

_DIRECTORY_TO_RUN = "./case"
_LB_HB_FILEPATH = "./lb_hb.tar.gz"
_ENERGYPLUS_FILE = "./EnergyPlus-8.8.0-7c3bbe4830-Linux-x86_64.sh"
_RADIANCE_FILE = "./radiance-5.1.0-Linux.tar.gz"
_COPY_TO_BLOB_FILE = ".copy_to_blob.py"
_RUN_PROCESS_FILEPATH = "./RunHoneybeeRadiance.py"

# Get start time to log length of time elapsed throughout process
start_time = datetime.datetime.now().replace(microsecond=0)
print('Sample start: {}'.format(start_time))
print()

# Create the pool containing the compute nodes executing the tasks
def select_latest_verified_vm_image_with_node_agent_sku(batch_client, publisher, offer, sku_starts_with):
    """
    Select the latest verified image that Azure Batch supports given a publisher, offer and sku (starts with filter).
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

def wrap_commands_in_shell(ostype, commands):
    """Wrap commands in a shell
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

def print_batch_exception(batch_exception):
    """
    Prints the contents of the specified Batch exception.
    :param batch_exception:
    """
    print('-------------------------------------------')
    print('Exception encountered:')
    if (batch_exception.error and batch_exception.error.message and
            batch_exception.error.message.value):
        print(batch_exception.error.message.value)
        if batch_exception.error.values:
            print()
            for mesg in batch_exception.error.values:
                print('{}:\t{}'.format(mesg.key, mesg.value))
    print('-------------------------------------------')

def create_pool(batch_service_client, pool_id, resource_files, publisher, offer, sku, node_count):
    """
    Creates a pool of compute nodes with the specified OS settings.
    :param batch_service_client: A Batch service client.
    :type batch_service_client: `azure.batch.BatchServiceClient`
    :param str pool_id: An ID for the new pool.
    :param list resource_files: A collection of resource files for the pool's start task.
    :param str publisher: Marketplace image publisher
    :param str offer: Marketplace image offer
    :param str sku: Marketplace image sku
    """
    print('Creating pool [{0:}]...'.format(pool_id))
    # Specify the commands for the pool's start task to be run on each node as it joins the pool.
    commands = [
        "curl -fSsL https://bootstrap.pypa.io/get-pip.py | python",  # Install pip
        "pip install azure-storage==0.32.0",  # Install the azure-storage module
        "sudo apt-get install docker -y && sudo apt-get install docker.io -y",  # Install docker
        "sudo docker pull tgerrish/bhrad"  # Pull RadHoneyWhale from docker hub
    ]
    # Get the node agent SKU and image reference for the virtual machine configuration.
    sku_to_use, image_ref_to_use = select_latest_verified_vm_image_with_node_agent_sku(
        batch_service_client,
        publisher,
        offer,
        sku
    )
    user = batchmodels.AutoUserSpecification(
        scope=batchmodels.AutoUserScope.pool,
        elevation_level=batchmodels.ElevationLevel.admin
    )
    new_pool = batch.models.PoolAddParameter(
        id=pool_id,
        virtual_machine_configuration=batchmodels.VirtualMachineConfiguration(
            image_reference=image_ref_to_use,
            node_agent_sku_id=sku_to_use),
        vm_size=_POOL_VM_SIZE,
        enable_auto_scale=True,
        auto_scale_formula='pendingTaskSamplePercent =$PendingTasks.GetSamplePercent(180 * TimeInterval_Second);pendingTaskSamples = pendingTaskSamplePercent < 70 ? 1 : avg($PendingTasks.GetSample(180 * TimeInterval_Second)); $TargetDedicatedNodes = min(100, pendingTaskSamples);',
        auto_scale_evaluation_interval=datetime.timedelta(minutes=5),
        start_task=batch.models.StartTask(
            command_line=wrap_commands_in_shell(
                "linux",
                commands),
            user_identity=batchmodels.UserIdentity(auto_user=user),
            wait_for_success=True,
            resource_files=resource_files),
    )

    try:
        batch_service_client.pool.add(
            new_pool
        )
    except batchmodels.batch_error.BatchErrorException as err:
        print_batch_exception(
            err
        )
        raise

_POOL_NODE_COUNT = len(_ANALYSIS_GRIDS)

pool = create_pool(batch_client, _POOL_ID, [_SKY_MTX, _SURFACES, _COPY_TO_BLOB], _NODE_OS_PUBLISHER, _NODE_OS_OFFER, _NODE_OS_SKU, _POOL_NODE_COUNT)

print("Pool created ...")