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

# Get the analysis grids to process, and the associated context shading and sky matrix
_SURFACES_FILEPATH = os.path.abspath(os.path.join(_DIRECTORY_TO_RUN, "surfaces.json"))
print("Surfaces file:\n{0:}\n".format(_SURFACES_FILEPATH))

_SKY_MTX_FILEPATH = os.path.abspath(os.path.join(_DIRECTORY_TO_RUN, "sky_mtx.json"))
print("Sky matrix file:\n{0:}\n".format(_SKY_MTX_FILEPATH))

_ANALYSIS_GRIDS_FILEPATHS = sorted([os.path.abspath(os.path.join(_DIRECTORY_TO_RUN, "AnalysisGrids", file)) for file in os.listdir(os.path.join(_DIRECTORY_TO_RUN, "AnalysisGrids")) if file.endswith(".json")])
print("Analysis grid files:")
for i in _ANALYSIS_GRIDS_FILEPATHS:
    print("{0:}".format(i))

# Create the blob client, for use in obtaining references to blob storage containers and uploading files to containers.
blob_client = azureblob.BlockBlobService(account_name=_STORAGE_ACCOUNT_NAME, account_key=_STORAGE_ACCOUNT_KEY)
print("Blob client created:\n{0:}".format(blob_client))

# Use the blob client to create the containers in Azure Storage if they don't yet exist.
input_container_name = 'input'
process_container_name = "process"
output_container_name = 'output'
blob_client.create_container(input_container_name, fail_on_exist=False)
print('Container [{}] created.'.format(input_container_name))
blob_client.create_container(process_container_name, fail_on_exist=False)
print('Container [{}] created.'.format(process_container_name))
blob_client.create_container(output_container_name, fail_on_exist=False)
print('Container [{}] created.'.format(output_container_name))

# Upload process files for processing the input files into the process directory
lb_hb_file = upload_file_to_container(blob_client, process_container_name, _LB_HB_FILEPATH)
run_process_file = upload_file_to_container(blob_client, process_container_name, _RUN_PROCESS_FILEPATH)

# Upload files for processing into the input directory
analysis_grid_files = [upload_file_to_container(blob_client, input_container_name, file_path) for file_path in _ANALYSIS_GRIDS_FILEPATHS]
surfaces_file = upload_file_to_container(blob_client, input_container_name, _SURFACES_FILEPATH)
sky_mtx_file = upload_file_to_container(blob_client, input_container_name, _SKY_MTX_FILEPATH)

# print("\nSurfaces blob:\n{0:}\n".format(surfaces_file))
# print("Sky matrix blob:\n{0:}\n".format(sky_mtx_file))
# print("Analysis grid blobs:")
# for i in analysis_grid_files:
#     print("{0:}".format(i))

# Obtain a shared access signature URL that provides write access to the output container to which the tasks will upload their output.
output_container_sas_url = get_container_sas_url(blob_client, output_container_name, azureblob.BlobPermissions.WRITE)
print(output_container_sas_url)

# Create a Batch service client. We'll now be interacting with the Batch service in addition to Storage
credentials = batchauth.SharedKeyCredentials(_BATCH_ACCOUNT_NAME, _BATCH_ACCOUNT_KEY)
print(credentials)
batch_client = batch.BatchServiceClient(credentials, base_url=_BATCH_ACCOUNT_URL)
print(batch_client)

# Create the job to which tasks will be assigned
print('Creating job [{}]...'.format(_JOB_ID))
batch_client.job.add(batch.models.JobAddParameter(_JOB_ID, batch.models.PoolInformation(pool_id=_POOL_ID)))

###############################################################
# Add tasks to the job

print('Adding {} tasks to job [{}]...'.format(len(analysis_grid_files), _JOB_ID))

tasks = []

for idx, analysis_grid_file in enumerate(analysis_grid_files):
    grid_file_path = analysis_grid_file.file_path
    sky_mtx_file_path = sky_mtx_file.file_path
    surfaces_file_path = surfaces_file.file_path
    results_file_path = grid_file_path.replace(".json", "_result.json")

    # print(grid_file_path, sky_mtx_file_path, surfaces_file_path, results_file_path)

    commands = [
        #         "docker run --name abc -t -d tgerrish/bhrad bash",
        "apt-get update",
        "apt-get install wget",
        "apt-get install rsync",
        "wget https://github.com/NREL/Radiance/releases/download/5.1.0/radiance-5.1.0-Linux.tar.gz",
        "tar xzf radiance-5.1.0-Linux.tar.gz",
        "rsync -av /radiance-5.1.0-Linux/usr/local/radiance/bin/ /usr/local/bin/",
        "rsync -av /radiance-5.1.0-Linux/usr/local/radiance/lib/ /usr/local/lib/ray/",
        "tar xzf lb_hb.tar.gz",
        "python3 RunHoneybeeRadiance.py -sm {0:} -s {1:} -p {2:}".format(sky_mtx_file_path, surfaces_file_path, grid_file_path),
        #         "docker run --name abc -v /var/run/docker.sock:/var/run/docker.sock -t -d tgerrish/bhrad bash",
        #         "docker cp ./{0:} abc:/surfaces.json".format(surfaces_file_path),
        #         "docker cp ./{0:} abc:/sky_mtx.json".format(sky_mtx_file_path),
        #         "docker cp ./{0:} abc:/{0:}".format(grid_file_path),
        #         "docker exec abc python RunHoneybeeRadiance.py -sm {0:} -s {1:} -p {2:}".format(sky_mtx_file_path, surfaces_file_path, grid_file_path),
        #         "docker cp abc:./{0:} ./{0:}".format(results_file_path),
        #         "docker stop abc",
        #         "docker rm abc"
    ]

    # print("\n{0:}\n".format("\n".join(commands)))

    command = wrap_commands_in_shell("linux", commands)

    # print(command)

    print()

    tasks.append(
        batch.models.TaskAddParameter(
            id='task_{0:}'.format(re.sub("[^0-9a-zA-Z]", "", grid_file_path.replace(".json", ""))),
            command_line=command,
            resource_files=[
                analysis_grid_file,
                sky_mtx_file,
                surfaces_file,
                lb_hb_file,
                run_process_file,
            ],
            output_files=[
                batchmodels.OutputFile(
                    results_file_path,
                    destination=batchmodels.OutputFileDestination(
                        container=batchmodels.OutputFileBlobContainerDestination(
                            output_container_sas_url
                        )
                    ),
                    upload_options=batchmodels.OutputFileUploadOptions(
                        batchmodels.OutputFileUploadCondition.task_success
                    )
                )
            ]
        )
    )

batch_tasks = batch_client.task.add_collection(_JOB_ID, tasks)

print(batch_tasks)
#######################################################################

# #######################################################################
# # Create the pool that will contain the compute nodes that will execute the tasks.
#
# print('Creating pool [{}]...'.format(_POOL_ID))
#
# commands = [
#     #     "apt-get update",
#     #     "apt-get install wget",
#     #     "apt-get install rsync",
#     #     "wget https://github.com/NREL/Radiance/releases/download/5.1.0/radiance-5.1.0-Linux.tar.gz",
#     #     "tar xzf radiance-5.1.0-Linux.tar.gz",
#     #     "rsync -av /radiance-5.1.0-Linux/usr/local/radiance/bin/ /usr/local/bin/",
#     #     "rsync -av /radiance-5.1.0-Linux/usr/local/radiance/lib/ /usr/local/lib/ray/",
#     #     "apt-get install docker -y",
#     #     "apt-get install docker.io -y",
#     #     "docker pull tgerrish/bhrad"
#     "ls",
#     "ls"
# ]
#
# command = wrap_commands_in_shell("linux", commands)
#
# new_pool = batch.models.PoolAddParameter(
#     id=_POOL_ID,
#     virtual_machine_configuration=batchmodels.VirtualMachineConfiguration(
#         image_reference=batchmodels.ImageReference(
#             publisher="Canonical",
#             offer="UbuntuServer",
#             sku="16.04-LTS",
#             version="latest"
#         ),
#         node_agent_sku_id="batch.node.ubuntu 16.04"
#     ),
#     vm_size=_POOL_VM_SIZE,
#     target_dedicated_nodes=_DEDICATED_POOL_NODE_COUNT,
#     target_low_priority_nodes=_LOW_PRIORITY_POOL_NODE_COUNT,
#     start_task=batchmodels.StartTask(
#         command_line=command,
#         wait_for_success=True,
#         user_identity=batchmodels.UserIdentity(
#             auto_user=batchmodels.AutoUserSpecification(
#                 scope=batchmodels.AutoUserScope.pool,
#                 elevation_level=batchmodels.ElevationLevel.admin
#             )
#         )
#     )
# )
#
# print(new_pool)
#
# batch_client.pool.add(new_pool)
# ##########################################################################
#
# ##########################################################################
# wait_for_tasks_to_complete(batch_client, _JOB_ID, datetime.timedelta(minutes=30))
# print("Success! All tasks reached the 'Completed' state within the specified timeout period.")
# ##########################################################################

