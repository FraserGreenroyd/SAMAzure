# TODO - map azure directory to docker container and run that way??

import datetime
import io
import os
import sys
import time

import azure.storage.blob as azureblob
import azure.batch.batch_service_client as batch
import azure.batch.batch_auth as batchauth
import azure.batch.models as batchmodels


# ************************************************** #
# ***   Public methods                           *** #
# ************************************************** #


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

    print('Uploading file {} to container [{}]...'.format(file_path, container_name))

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


def create_pool(batch_service_client, pool_id):
    """
    Creates a pool of compute nodes with the specified OS settings.

    :param batch_service_client: A Batch service client.
    :type batch_service_client: `azure.batch.BatchServiceClient`
    :param str pool_id: An ID for the new pool.
    :param str publisher: Marketplace image publisher
    :param str offer: Marketplace image offer
    :param str sku: Marketplace image sku
    """
    print('Creating pool [{}]...'.format(pool_id))

    # Create a new pool of Linux compute nodes using an Azure Virtual Machines Marketplace image. For more information about creating pools of Linux nodes, see https://azure.microsoft.com/documentation/articles/batch-linux-nodes/

    # The start task installs ffmpeg on each node from an available repository, using an administrator user identity.

    # pool_command = "/bin/bash -c \"apt-get update && apt-get install -y ffmpeg\""
    commands = [
        "curl -fSsL https://bootstrap.pypa.io/get-pip.py | python",  # Install pip
        "pip install azure-storage==0.32.0",  # Install the azure-storage module
        "sudo apt-get install docker -y && sudo apt-get install docker.io -y",  # Install docker
        "sudo docker pull tgerrish/bhrad"  # Pull tgerrish/bhrad from docker hub
    ]
    pool_command = wrap_commands_in_shell("linux", commands)

    new_pool = batch.models.PoolAddParameter(
        id=pool_id,
        virtual_machine_configuration=batchmodels.VirtualMachineConfiguration(
            image_reference=batchmodels.ImageReference(publisher="Canonical", offer="UbuntuServer", sku="16.04-LTS",
                                                       version="latest"), node_agent_sku_id="batch.node.ubuntu 16.04"),
        vm_size=_POOL_VM_SIZE,
        target_dedicated_nodes=_DEDICATED_POOL_NODE_COUNT,
        target_low_priority_nodes=_LOW_PRIORITY_POOL_NODE_COUNT,
        start_task=batchmodels.StartTask(command_line=pool_command, wait_for_success=True,
                                         user_identity=batchmodels.UserIdentity(
                                             auto_user=batchmodels.AutoUserSpecification(
                                                 scope=batchmodels.AutoUserScope.pool,
                                                 elevation_level=batchmodels.ElevationLevel.admin)))
    )

    batch_service_client.pool.add(new_pool)


def create_job(batch_service_client, job_id, pool_id):
    """
    Creates a job with the specified ID, associated with the specified pool.

    :param batch_service_client: A Batch service client.
    :type batch_service_client: `azure.batch.BatchServiceClient`
    :param str job_id: The ID for the job.
    :param str pool_id: The ID for the pool.
    """
    print('Creating job [{}]...'.format(job_id))

    job = batch.models.JobAddParameter(job_id, batch.models.PoolInformation(pool_id=pool_id))

    batch_service_client.job.add(job)


def add_tasks(batch_service_client, job_id, analysis_grid_files, sky_mtx_file, surfaces_file, output_container_sas_url):
    """
    Adds a task for each input file in the collection to the specified job.

    :param batch_service_client: A Batch service client.
    :type batch_service_client: `azure.batch.BatchServiceClient`
    :param str job_id: The ID of the job to which to add the tasks.
    :param list analysis_grid_files: A collection of input files. One task will be created for each input file.
    :param str sky_mtx_file: A sky matrix JSON to pass with the analysis grids.
:   :param str surfaces_file: A surfaces JSON to pass with the analysis grids.
    :param output_container_sas_token: A SAS token granting write access to the specified Azure Blob storage container.
    """

    print('Adding {} tasks to job [{}]...'.format(len(analysis_grid_files), job_id))

    tasks = list()

    for idx, grid_file in enumerate(analysis_grid_files):
        grid_file_path = grid_file.file_path
        sky_mtx_file_path = sky_mtx_file.file_path
        surfaces_file_path = surfaces_file.file_path
        result_file_path = grid_file_path.replace(".json", "_result.json")

        # print(grid_file_path)

        commands = [
            #"sudo bash",
            "docker run --name abc -t -d tgerrish/bhrad bash",
            "docker cp ./{0:} abc:/surfaces.json".format(surfaces_file_path),
            "docker cp ./{0:} abc:/sky_mtx.json".format(sky_mtx_file_path),
            "docker cp ./{0:} abc:/{0:}".format(grid_file_path),
            "docker exec abc python RunHoneybeeRadiance.py -sm {0:} -s {1:} -p {2:}".format(sky_mtx_file_path, surfaces_file_path, grid_file_path),
            "docker cp abc:/{0:} ./{0:}".format(result_file_path),
            "docker stop abc",
            "docker rm abc"
        ]
        command = wrap_commands_in_shell("linux", commands)

        tasks.append(
            batch.models.TaskAddParameter(id='Task{}'.format(idx), command_line=command, resource_files=[grid_file, sky_mtx_file, surfaces_file],
                                          output_files=[batchmodels.OutputFile(result_file_path,
                                                                               destination=batchmodels.OutputFileDestination(
                                                                                   container=batchmodels.OutputFileBlobContainerDestination(
                                                                                       output_container_sas_url)),
                                                                               upload_options=batchmodels.OutputFileUploadOptions(
                                                                                   batchmodels.OutputFileUploadCondition.task_success))]))

    batch_service_client.task.add_collection(job_id, tasks)


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


# ************************************************** #
# ***   Main execution                           *** #
# ************************************************** #


# GLOBAL
_BATCH_ACCOUNT_NAME = "climatebasedbatch"
_BATCH_ACCOUNT_KEY = "W94ukoxG2neFkk6teOVZ3IQ8IQjmPJqPcFq48I9lLzCrPEQSRFS/+euaUEkkSyPoulUgnx5IEZxztA9574Hluw=="
_BATCH_ACCOUNT_URL = "https://climatebasedbatch.westeurope.batch.azure.com"

_STORAGE_ACCOUNT_NAME = "radfiles"
_STORAGE_ACCOUNT_KEY = "aRRVzOkO/kwS35CIwNVIa18aGoMfZD5D3yAy3GlorkkU2G+9q5rAscXoC21IIylJZerBefwMgxYYF3qzquALrw=="

_POOL_ID = 'radbatchpool'
_DEDICATED_POOL_NODE_COUNT = 0
_LOW_PRIORITY_POOL_NODE_COUNT = 4
_POOL_VM_SIZE = 'STANDARD_A1_v2'
_JOB_ID = 'radbatchjob'

_DIRECTORY_TO_RUN = "./radfiles"

# Get start time to log length of time elapsed throughout process
start_time = datetime.datetime.now().replace(microsecond=0)
print('Sample start: {}'.format(start_time))
print()

# Get the analysis grids to process and the associated context shading and sky matrix
_SURFACES_FILEPATH = os.path.abspath(os.path.join(_DIRECTORY_TO_RUN, "surfaces.json"))
_SKY_MTX_FILEPATH = os.path.abspath(os.path.join(_DIRECTORY_TO_RUN, "sky_mtx.json"))
_ANALYSIS_GRIDS_FILEPATHS = sorted([os.path.abspath(os.path.join(_DIRECTORY_TO_RUN, "AnalysisGrids", i)) for i in os.listdir(os.path.join(_DIRECTORY_TO_RUN, "AnalysisGrids"))])
# print(_SURFACES_FILEPATH, _SKY_MTX_FILEPATH, _ANALYSIS_GRIDS_FILEPATHS)

# Create the blob client, for use in obtaining references to blob storage containers and uploading files to containers.
blob_client = azureblob.BlockBlobService(account_name=_STORAGE_ACCOUNT_NAME, account_key=_STORAGE_ACCOUNT_KEY)

# Use the blob client to create the containers in Azure Storage if they don't yet exist.
input_container_name = 'input'
output_container_name = 'output'
blob_client.create_container(input_container_name, fail_on_exist=False)
blob_client.create_container(output_container_name, fail_on_exist=False)
print('Container [{}] created.'.format(input_container_name))
print('Container [{}] created.'.format(output_container_name))

# Upload files for processing into the input directory
analysis_grid_files = [upload_file_to_container(blob_client, input_container_name, file_path) for file_path in _ANALYSIS_GRIDS_FILEPATHS]
surfaces_file = upload_file_to_container(blob_client, input_container_name, _SURFACES_FILEPATH)
sky_mtx_file = upload_file_to_container(blob_client, input_container_name, _SKY_MTX_FILEPATH)

# Obtain a shared access signature URL that provides write access to the output container to which the tasks will upload their output.
output_container_sas_url = get_container_sas_url(blob_client, output_container_name, azureblob.BlobPermissions.WRITE)

# Create a Batch service client. We'll now be interacting with the Batch service in addition to Storage
credentials = batchauth.SharedKeyCredentials(_BATCH_ACCOUNT_NAME, _BATCH_ACCOUNT_KEY)
batch_client = batch.BatchServiceClient(credentials, base_url=_BATCH_ACCOUNT_URL)

# Delete the job if it already exists and wait a bit to let it delete
try:
    batch_client.job.delete(_JOB_ID)
    print("Job [{0:}] deleted".format(_JOB_ID))
    for i in range(10):
        print(10 - i)
        time.sleep(1)
    print()
except:
    pass

# create_job(batch_client, _JOB_ID, _POOL_ID)

# add_tasks(batch_client, _JOB_ID, analysis_grid_files, sky_mtx_file, surfaces_file, output_container_sas_url)

try:
    # Create the pool that will contain the compute nodes that will execute the tasks.
    create_pool(batch_client, _POOL_ID)
    # Create the job that will run the tasks.
    create_job(batch_client, _JOB_ID, _POOL_ID)
    # Add the tasks to the job. Pass the input files and a SAS URL to the storage container for output files.
    add_tasks(batch_client, _JOB_ID, analysis_grid_files, sky_mtx_file, surfaces_file, output_container_sas_url)
    # Pause execution until tasks reach Completed state.
    wait_for_tasks_to_complete(batch_client, _JOB_ID, datetime.timedelta(minutes=30))
    print("  Success! All tasks reached the 'Completed' state within the specified timeout period.")
except batchmodels.batch_error.BatchErrorException as err:
    print_batch_exception(err)
    raise
#
print()
#
# Delete input container in storage
print('Deleting container [{}]...'.format(input_container_name))
blob_client.delete_container(input_container_name)
# Print out some timing info
end_time = datetime.datetime.now().replace(microsecond=0)
print()
print('Sample end: {}'.format(end_time))
print('Elapsed time: {}'.format(end_time - start_time))
print()
# Clean up Batch resources (if the user so chooses).
if query_yes_no('Delete job?') == 'yes':
    batch_client.job.delete(_JOB_ID)
if query_yes_no('Delete pool?') == 'yes':
    batch_client.pool.delete(_POOL_ID)
print()
input('Press ENTER to exit...')
