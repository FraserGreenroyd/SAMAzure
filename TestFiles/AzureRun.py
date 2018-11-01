# call "C:\Users\tgerrish\AppData\Local\Continuum\anaconda2\Scripts\activate.bat" && activate azurebatch

# TODO: Add some prints for process feedback

from __future__ import print_function

try:
    import configparser
except ImportError:
    import ConfigParser as configparser

import datetime
import os
import argparse
import re  # for file renaming

import azure.storage.blob as azureblob
import azure.batch.batch_service_client as batch
import azure.batch.batch_auth as batchauth
import azure.batch.models as batchmodels

import common.helpers

# def create_pool(batch_client, block_blob_client, pool_id, vm_size, vm_count):
#     """Creates an Azure Batch pool with the specified id.
#
#     :param batch_client: The batch client to use.
#     :type batch_client: `batchserviceclient.BatchServiceClient`
#     :param block_blob_client: The storage block blob client to use.
#     :type block_blob_client: `azure.storage.blob.BlockBlobService`
#     :param str pool_id: The id of the pool to create.
#     :param str vm_size: vm size (sku)
#     :param int vm_count: number of vms to allocate
#     """
#     # pick the latest supported 16.04 sku for UbuntuServer
#     sku_to_use, image_ref_to_use = \
#         common.helpers.select_latest_verified_vm_image_with_node_agent_sku(
#             batch_client, 'Canonical', 'UbuntuServer', '16.04')
#
#     block_blob_client.create_container(_CONTAINER_NAME, fail_on_exist=False)
#
#     # sas_url = common.helpers.upload_blob_and_create_sas(
#     #     block_blob_client,
#     #     _CONTAINER_NAME,
#     #     _SIMPLE_TASK_NAME,
#     #     _SIMPLE_TASK_PATH,
#     #     datetime.datetime.utcnow() + datetime.timedelta(hours=1))
#
#     # TODO - check to see where these files are on the node - make node accesible via CLI?
#     pool_start_commands = [
#         "cd",
#         "cd /",
#         "sudo cp -p radiance-5.1.0-Linux.tar.gz $AZ_BATCH_NODE_SHARED_DIR",
#         "sudo tar xzf radiance-5.1.0-Linux.tar.gz",
#         "sudo rsync -av /radiance-5.1.0-Linux/usr/local/radiance/bin/ /usr/local/bin/",
#         "sudo rsync -av /radiance-5.1.0-Linux/usr/local/radiance/lib/ /usr/local/lib/ray/",
#         "sudo cp -p lb_hb.tar.gz $AZ_BATCH_NODE_SHARED_DIR",
#         "sudo tar xzf lb_hb.tar.gz",
#         "sudo cp -p RunHoneybeeRadiance.py $AZ_BATCH_NODE_SHARED_DIR",
#     ]
#
#     pool = batchmodels.PoolAddParameter(
#         id=pool_id,
#         virtual_machine_configuration=batchmodels.VirtualMachineConfiguration(
#             image_reference=image_ref_to_use,
#             node_agent_sku_id=sku_to_use),
#         vm_size=vm_size,
#         target_dedicated_nodes=vm_count,
#         start_task=batchmodels.StartTask(
#             command_line=common.helpers.wrap_commands_in_shell("linux", pool_start_commands),
#             resource_files=[
#                 batchmodels.ResourceFile(file_path=_RADIANCE_PROGRAM_NAME, blob_source=_RADIANCE_PROGRAM_SAS_URL),
#                 batchmodels.ResourceFile(file_path=_LB_HB_NAME, blob_source=_LB_HB_SAS_URL),
#                 batchmodels.ResourceFile(file_path=_SCRIPT_NAME, blob_source=_SCRIPT_SAS_URL),
#             ]))
#
#     common.helpers.create_pool_if_not_exist(batch_client, pool)


# def submit_job_and_add_task(batch_client, block_blob_client, job_id, pool_id):
#     """Submits a job to the Azure Batch service and adds
#     a task that runs a python script.
#
#     :param batch_client: The batch client to use.
#     :type batch_client: `batchserviceclient.BatchServiceClient`
#     :param block_blob_client: The storage block blob client to use.
#     :type block_blob_client: `azure.storage.blob.BlockBlobService`
#     :param str job_id: The id of the job to create.
#     :param str pool_id: The id of the pool to use.
#     """
#
#     block_blob_client.create_container(_CONTAINER_NAME, fail_on_exist=False)
#
#     # Upload the surfaces and sky_mtx files
#     # sas_url = common.helpers.upload_blob_and_create_sas(
#     #     block_blob_client,
#     #     _CONTAINER_NAME,
#     #     _SIMPLE_TASK_NAME,
#     #     _SIMPLE_TASK_PATH,
#     #     datetime.datetime.utcnow() + datetime.timedelta(hours=1))
#
#     surfaces_sas_url = common.helpers.upload_blob_and_create_sas(
#         block_blob_client,
#         _CONTAINER_NAME,
#         "surfaces.json",
#         _SURFACES_PATH,
#         datetime.datetime.utcnow() + datetime.timedelta(hours=12))
#
#     sky_mtx_sas_url = common.helpers.upload_blob_and_create_sas(
#         block_blob_client,
#         _CONTAINER_NAME,
#         "sky_mtx.json",
#         _SKY_MTX_PATH,
#         datetime.datetime.utcnow() + datetime.timedelta(hours=12))
#
#     analysis_grid_sas_urls = []
#     analysis_grid_names = []
#     for _GRID_FILE in _ANALYSIS_GRID_PATHS:
#         _GRID_NAME = os.path.basename(_GRID_FILE)
#         analysis_grid_sas_urls.append(
#             common.helpers.upload_blob_and_create_sas(
#             block_blob_client,
#             _CONTAINER_NAME,
#             _GRID_NAME,
#             _GRID_FILE,
#             datetime.datetime.utcnow() + datetime.timedelta(hours=12)))
#         analysis_grid_names.append(_GRID_NAME)
#
#     # Create a job for each group of 100 analysis grids (maximum number of task per job = 100)
#     job = batchmodels.JobAddParameter(id=job_id, pool_info=batchmodels.PoolInformation(pool_id=pool_id))
#
#     batch_client.job.add(job)
#
#     # Create a task per analysis grid
#     tasks = []
#     for n, grid_sas_url in enumerate(analysis_grid_sas_urls):
#         tasks.append(batchmodels.TaskAddParameter(
#             id=analysis_grid_names[n].replace(".json", ""),
#             command_line="cd && cd / && python RunRadiance.py",
#             resource_files=[
#                 batchmodels.ResourceFile(file_path=analysis_grid_names[n], blob_source=grid_sas_url),
#                 batchmodels.ResourceFile(file_path="sky_mtx.json", blob_source=sky_mtx_sas_url),
#                 batchmodels.ResourceFile(file_path="surfaces.json", blob_source=surfaces_sas_url),
#             ],
#             output_files=[
#                 batchmodels.OutputFile(
#                     file_pattern=analysis_grid_names[n].replace(".json", "_result.json"),
#                     destination=batchmodels.OutputFileDestination(container=_CONTAINER_NAME),
#                     upload_options=batchmodels.OutputFileUploadOptions(upload_condition="taskCompletion"))]))
#
#     [batch_client.task.add(job_id=job.id, task=task) for task in tasks]


# def execute_sample(config):
#     """Executes the sample with the specified configurations.
#
#     :param config: The global configuration to use.
#     :type config: `configparser.ConfigParser`
#     """
#     # Set up the configuration
#     batch_account_key = config.get('Batch', 'batchaccountkey').replace("%", "%%")
#     batch_account_name = config.get('Batch', 'batchaccountname').replace("%", "%%")
#     batch_service_url = config.get('Batch', 'batchserviceurl').replace("%", "%%")
#
#     storage_account_key = config.get('Storage', 'storageaccountkey').replace("%", "%%")
#     storage_account_name = config.get('Storage', 'storageaccountname').replace("%", "%%")
#     storage_account_suffix = config.get('Storage', 'storageaccountsuffix').replace("%", "%%")
#
#     should_delete_container = config.getboolean('Default', 'shoulddeletecontainer')
#     should_delete_job = config.getboolean('Default', 'shoulddeletejob')
#     should_delete_pool = config.getboolean('Default', 'shoulddeletepool')
#     pool_vm_size = config.get('Default', 'poolvmsize')
#     pool_vm_count = config.getint('Default', 'poolvmcount')
#
#     # Print the settings we are running with
#     # common.helpers.print_configuration(config)
#
#     credentials = batchauth.SharedKeyCredentials(batch_account_name, batch_account_key)
#     batch_client = batch.BatchServiceClient(credentials, base_url=batch_service_url)
#
#     # Retry 5 times -- default is 3
#     batch_client.config.retry_policy.retries = 3
#
#     block_blob_client = azureblob.BlockBlobService(
#         account_name=storage_account_name,
#         account_key=storage_account_key,
#         endpoint_suffix=storage_account_suffix)
#
#     job_id = common.helpers.generate_unique_resource_name("batch_job")
#     pool_id = "batch_pool"
#
#     try:
#         create_pool(batch_client, block_blob_client, pool_id, pool_vm_size, pool_vm_count)
#
#         submit_job_and_add_task(batch_client, block_blob_client, job_id, pool_id)
#
#         common.helpers.wait_for_tasks_to_complete(batch_client, job_id, datetime.timedelta(minutes=25))
#
#         tasks = batch_client.task.list(job_id)
#         task_ids = [task.id for task in tasks]
#
#         common.helpers.print_task_output(batch_client, job_id, task_ids)
#     finally:
#         # clean up
#         if should_delete_container:
#             block_blob_client.delete_container(_CONTAINER_NAME, fail_not_exist=False)
#         if should_delete_job:
#             print("Deleting job: ", job_id)
#             batch_client.job.delete(job_id)
#         if should_delete_pool:
#             print("Deleting pool: ", pool_id)
#             batch_client.pool.delete(pool_id)


if __name__ == '__main__':

    print("###############################")
    print("########### START #############")

    # Obtain locations of global configuration and radiance case
    _CONFIGURATION_PATH = os.path.join('common', 'configuration.cfg')
    _CONTAINER_NAME = 'test-batch-container'
    _RADIANCE_CASE_PATH = os.path.join('resources', 'radiance_case')

    # Get the case details from the _RADIANCE_CASE_PATH
    _SURFACES_PATH = os.path.join(_RADIANCE_CASE_PATH, "surfaces.json")
    _SKY_MTX_PATH = os.path.join(_RADIANCE_CASE_PATH, "sky_mtx.json")
    _ANALYSIS_GRID_PATHS = common.helpers.find_files(os.path.join(_RADIANCE_CASE_PATH, "AnalysisGrids"), ".json")

    # Obtain credentials and global variables from the configuration file
    config = configparser.RawConfigParser()
    config.read(_CONFIGURATION_PATH)

    batch_account_key = config.get('Batch', 'batchaccountkey').replace("%", "%%")
    batch_account_name = config.get('Batch', 'batchaccountname').replace("%", "%%")
    batch_service_url = config.get('Batch', 'batchserviceurl').replace("%", "%%")
    storage_account_key = config.get('Storage', 'storageaccountkey').replace("%", "%%")
    storage_account_name = config.get('Storage', 'storageaccountname').replace("%", "%%")
    storage_account_suffix = config.get('Storage', 'storageaccountsuffix').replace("%", "%%")
    should_delete_container = config.getboolean('Default', 'shoulddeletecontainer')
    should_delete_job = config.getboolean('Default', 'shoulddeletejob')
    should_delete_pool = config.getboolean('Default', 'shoulddeletepool')
    pool_vm_size = config.get('Default', 'poolvmsize')
    pool_vm_count = config.getint('Default', 'poolvmcount')

    # Generate batch client
    credentials = batchauth.SharedKeyCredentials(batch_account_name, batch_account_key)
    batch_client = batch.BatchServiceClient(credentials, base_url=batch_service_url)

    # Generate blob client
    block_blob_client = azureblob.BlockBlobService(
        account_name=storage_account_name,
        account_key=storage_account_key,
        endpoint_suffix=storage_account_suffix)
    block_blob_client.

    # Upload files to blob, and obtain names and sas urls
    block_blob_client.create_container(_CONTAINER_NAME, fail_on_exist=False)
    block_blob_client.
    # container_sas_url = "https://{0:}.blob.core.windows.net/{1:}?{2:}".format(storage_account_name, _CONTAINER_NAME, storage_account_key)
    # print(container_sas_url)

    surfaces_sas_url = common.helpers.upload_blob_and_create_sas(
        block_blob_client,
        _CONTAINER_NAME,
        "surfaces.json",
        _SURFACES_PATH,
        datetime.datetime.utcnow() + datetime.timedelta(hours=12))

    sky_mtx_sas_url = common.helpers.upload_blob_and_create_sas(
        block_blob_client,
        _CONTAINER_NAME,
        "sky_mtx.json",
        _SKY_MTX_PATH,
        datetime.datetime.utcnow() + datetime.timedelta(hours=12))

    analysis_grid_sas_urls = []
    analysis_grid_names = []
    for _GRID_FILE in _ANALYSIS_GRID_PATHS:
        _GRID_NAME = os.path.basename(_GRID_FILE)
        analysis_grid_sas_urls.append(
            common.helpers.upload_blob_and_create_sas(
                block_blob_client,
                _CONTAINER_NAME,
                _GRID_NAME,
                _GRID_FILE,
                datetime.datetime.utcnow() + datetime.timedelta(hours=12)))
        analysis_grid_names.append(_GRID_NAME)

    # Get a verified VM image on which to run the job/s
    sku_to_use, image_ref_to_use = \
        common.helpers.select_latest_verified_vm_image_with_node_agent_sku(
            batch_client, 'Canonical', 'UbuntuServer', '16.04')

    # Commands passed to all nodes in pool on creation
    pool_start_commands = [
        "cd / ",
        # "wget --no-check-certificate https://github.com/FraserGreenroyd/SAMAzure/raw/master/TestFiles/resources/azure_common/radiance-5.1.0-Linux.tar.gz",
        # "tar xzf radiance-5.1.0-Linux.tar.gz",
        # "rsync -av /radiance-5.1.0-Linux/usr/local/radiance/bin/ /usr/local/bin/",
        # "rsync -av /radiance-5.1.0-Linux/usr/local/radiance/lib/ /usr/local/lib/ray/",
        # "wget --no-check-certificate https://github.com/FraserGreenroyd/SAMAzure/raw/master/TestFiles/resources/azure_common/lb_hb.tar.gz",
        # "tar xzf lb_hb.tar.gz",
        # "wget --no-check-certificate https://github.com/FraserGreenroyd/SAMAzure/raw/master/TestFiles/resources/azure_common/RunHoneybeeRadiance.py"
    ]

    pool_user = batchmodels.UserIdentity(
        auto_user=batchmodels.AutoUserSpecification(
            elevation_level=batchmodels.ElevationLevel.admin,
            scope=batchmodels.AutoUserScope.pool))

    pool_id = common.helpers.generate_unique_resource_name("batchpool")

    pool = batchmodels.PoolAddParameter(
        id=pool_id,
        vm_size=pool_vm_size,
        virtual_machine_configuration=batchmodels.VirtualMachineConfiguration(image_reference=image_ref_to_use, node_agent_sku_id=sku_to_use),
        target_dedicated_nodes=1,
        # enable_auto_scale=True,
        # auto_scale_formula="pendingTaskSamplePercent = $PendingTasks.GetSamplePercent(180 * TimeInterval_Second);pendingTaskSamples = pendingTaskSamplePercent < 70 ? 1 : avg($PendingTasks.GetSample(180 * TimeInterval_Second)); $TargetDedicatedNodes = min(100, pendingTaskSamples);",
        # auto_scale_evaluation_interval=datetime.timedelta(minutes=5),
        start_task=batchmodels.StartTask(
            user_identity=pool_user,
            command_line=common.helpers.wrap_commands_in_shell("linux", pool_start_commands),
            resource_files=[]
        ),
    )

    common.helpers.create_pool_if_not_exist(batch_client, pool)

    job_id = common.helpers.generate_unique_resource_name("batchjob")

    job = batchmodels.JobAddParameter(id=job_id, pool_info=batchmodels.PoolInformation(pool_id=pool_id))

    batch_client.job.add(job)

    task_user = batchmodels.UserIdentity(
        auto_user=batchmodels.AutoUserSpecification(
            elevation_level=batchmodels.ElevationLevel.admin,
            scope=batchmodels.AutoUserScope.task))

    task_id = common.helpers.generate_unique_resource_name("task")

    # TODO: Check for "job-n" in mnt directory below when adding scalability
    # TODO: Remove hard coded grid file (once number of nodes made to match grid files)
    task_run_commands = [
        "cd /",
        # "sudo apt-get -y install python-pip",
        # "sudo pip install azure-storage",
        "sudo wget --no-check-certificate https://github.com/FraserGreenroyd/SAMAzure/raw/master/TestFiles/resources/azure_common/CopyToBlob.py",
        "sudo wget --no-check-certificate https://github.com/FraserGreenroyd/SAMAzure/raw/master/TestFiles/resources/azure_common/radiance-5.1.0-Linux.tar.gz",
        "sudo tar xzf radiance-5.1.0-Linux.tar.gz",
        "sudo rsync -av /radiance-5.1.0-Linux/usr/local/radiance/bin/ /usr/local/bin/",
        "sudo rsync -av /radiance-5.1.0-Linux/usr/local/radiance/lib/ /usr/local/lib/ray/",
        "sudo wget --no-check-certificate https://github.com/FraserGreenroyd/SAMAzure/raw/master/TestFiles/resources/azure_common/lb_hb.tar.gz",
        "sudo tar xzf lb_hb.tar.gz",
        "sudo wget --no-check-certificate https://github.com/FraserGreenroyd/SAMAzure/raw/master/TestFiles/resources/azure_common/RunHoneybeeRadiance.py",
        "sudo python RunHoneybeeRadiance.py -s ./mnt/batch/tasks/workitems/{0:}/job-1/{1:}/wd/surfaces.json -sm ./mnt/batch/tasks/workitems/{0:}/job-1/{1:}/wd/sky_mtx.json -p ./mnt/batch/tasks/workitems/{0:}/job-1/{1:}/wd/{2:}".format(job_id, task_id, analysis_grid_names[0]),
        # "sudo python CopyToBlob.py -fp /mnt/batch/tasks/workitems/{0:}/job-1/{1:}/wd/{2:} -bn {2:} -sa {3:} -sc {4:} -st {5:}".format(
        #     job_id,
        #     task_id,
        #     analysis_grid_names[0].replace(".json", "_result.json"),
        #     storage_account_name,
        #     _CONTAINER_NAME,
        #     storage_account_key
        # )
    ]

    task = batchmodels.TaskAddParameter(
        id=task_id,
        command_line=common.helpers.wrap_commands_in_shell("linux", task_run_commands),
        resource_files=[
            batchmodels.ResourceFile(file_path=analysis_grid_names[0], blob_source=analysis_grid_sas_urls[0]),
            batchmodels.ResourceFile(file_path="sky_mtx.json", blob_source=sky_mtx_sas_url),
            batchmodels.ResourceFile(file_path="surfaces.json", blob_source=surfaces_sas_url),
        ],
        output_files=[
            batchmodels.OutputFile(
                file_pattern="*result.json",
                destination=batchmodels.OutputFileDestination(container=batchmodels.OutputFileBlobContainerDestination(container_url=container_sas_url)),
                upload_options=batchmodels.OutputFileUploadOptions(upload_condition="taskCompletion"))],
        user_identity=task_user)

    # print("Results written to ./mnt/batch/tasks/workitems/{0:}/job-1/{1:}/wd/{2:} on the node".format(job_id, task_id, analysis_grid_names[0].replace(".json", "_result.json")))

    batch_client.task.add(job_id=job_id, task=task)

















    #batch_client.task.add(job_id=job.id, task=task)

    # Create a job for each group of 100 analysis grids (maximum number of task per job = 100)
    # job = batchmodels.JobAddParameter(id=job_id, pool_info=batchmodels.PoolInformation(pool_id=pool_id))
    #
    # batch_client.job.add(job)
    #
    # # Create a task per analysis grid
    # tasks = []
    # for n, grid_sas_url in enumerate(analysis_grid_sas_urls):
    #     tasks.append(batchmodels.TaskAddParameter(
    #         id=analysis_grid_names[n].replace(".json", ""),
    #         command_line="cd && cd / && python RunRadiance.py",
    #         resource_files=[
    #             batchmodels.ResourceFile(file_path=analysis_grid_names[n], blob_source=grid_sas_url),
    #             batchmodels.ResourceFile(file_path="sky_mtx.json", blob_source=sky_mtx_sas_url),
    #             batchmodels.ResourceFile(file_path="surfaces.json", blob_source=surfaces_sas_url),
    #         ],
    #         output_files=[
    #             batchmodels.OutputFile(
    #                 file_pattern=analysis_grid_names[n].replace(".json", "_result.json"),
    #                 destination=batchmodels.OutputFileDestination(container=_CONTAINER_NAME),
    #                 upload_options=batchmodels.OutputFileUploadOptions(upload_condition="taskCompletion"))]))
    #
    # [batch_client.task.add(job_id=job.id, task=task) for task in tasks]

    print("########### FINISH ############")
    print("###############################")

# if __name__ == '__main__':
#
#     parser = argparse.ArgumentParser(description="Send job to Azure")
#
#     parser.add_argument(
#         "-d",
#         "--caseDirectory",
#         type=str,
#         help="Path to the case directory from which simulation ingredients are obtained",
#         default="./case")  # TODO - Remove post testing
#     parser.add_argument(
#         "-c",
#         "--configFile",
#         type=str,
#         help="Path to the azure config file",
#         default="./common/configuration.cfg")  # TODO - Remove post testing
#     parser.add_argument(
#         "-j",
#         "--jobID",
#         type=str,
#         help="ID for the job being undertaken",
#         default="0000000-testjob-3513")  # TODO - Remove post testing
#
#     args = parser.parse_args()
#
#     _CASE_DIRECTORY = args.caseDirectory
#     _JOB_ID = args.jobID
#     _CONFIG_FILE = args.configFile
#
#     global_config = configparser.RawConfigParser()
#     global_config.read(_CONFIG_FILE)
#
#     _BATCH_ACCOUNT_NAME = global_config.get("Batch", "batchaccountname")
#     _BATCH_ACCOUNT_KEY = global_config.get("Batch", "batchaccountkey")
#     _BATCH_ACCOUNT_URL = global_config.get("Batch", "batchserviceurl")
#     _STORAGE_ACCOUNT_NAME = global_config.get("Storage", "storageaccountname")
#     _STORAGE_ACCOUNT_KEY = global_config.get("Storage", "storageaccountkey")
#     _STORAGE_ACCOUNT_SUFFIX = global_config.get("Storage", "storageaccountsuffix")
#     _POOL_ID = global_config.get("Default", "poolid")
#     _POOL_VM_SIZE = global_config.get("Default", "poolvmsize")
#     _MIN_POOL_NODE = global_config.getint("Default", "poolvmcountmin")
#     _MAX_POOL_NODE = global_config.getint("Default", "poolvmcountmax")
#     _NODE_OS_PUBLISHER = global_config.get("Default", "nodepublisher")
#     _NODE_OS_OFFER = global_config.get("Default", "nodeoffer")
#     _NODE_OS_SKU = global_config.get("Default", "nodesku")
#
#     _RADIANCE_SAS_TOKEN = global_config.get("Process", "radiancesastoken")
#     _RADIANCE_SAS_URL = global_config.get("Process", "radiancesasurl")
#     _LB_HB_SAS_TOKEN = global_config.get("Process", "lbhbsastoken")
#     _LB_HB_SAS_URL = global_config.get("Process", "lbhbsasurl")
#     _SCRIPT_SAS_TOKEN = global_config.get("Process", "scriptsastoken")
#     _SCRIPT_SAS_URL = global_config.get("Process", "scriptsasurl")
#     _COPYTOBLOB_SAS_TOKEN = global_config.get("Process", "copytoblobsastoken")
#     _COPYTOBLOB_SAS_URL = global_config.get("Process", "copytoblobsasurl")
#
#     _DELETE_CONTAINER = global_config.getboolean("Default", "shoulddeletecontainer")
#     _DELETE_JOB = global_config.getboolean("Default", "shoulddeletejob")
#     _DELETE_POOL = global_config.getboolean("Default", "shoulddeletepool")
#
#     print("\n\n\nStarting ... \n\n\n")
#
#     ####################
#     # Upload the files #
#     ####################
#
#     # File accessibility expiry time
#     expiry = datetime.datetime.utcnow() + datetime.timedelta(minutes=global_config.getint("Default", "blobreadtimeout"))
#     print("Files accessible until: {0:}".format(expiry.strftime("%Y-%m-%d %H:%M")))
#
#     # Create the blob client
#     blob_client = azureblob.BlockBlobService(account_name=_STORAGE_ACCOUNT_NAME, account_key=_STORAGE_ACCOUNT_KEY)
#     print("Blob client generated")
#
#     # # Tidying up - if the files already exist
#     # try:
#     #     blob_client.delete_container(_JOB_ID)
#     # except:
#     #     pass
#
#     print("")
#
#     # Create a job container
#     blob_client.create_container(_JOB_ID, fail_on_exist=False)
#     container_sas_token = blob_client.generate_container_shared_access_signature(_JOB_ID, permission=azureblob.BlobPermissions(read=True, write=True), expiry=expiry)
#     output_container_sas_url = "https://{0:}.blob.core.windows.net/{1:}?{2:}".format(_STORAGE_ACCOUNT_NAME, _JOB_ID, container_sas_token)
#     print('[{0:}] container created.'.format(_JOB_ID))
#
#     # Upload case files to job container
#     _SKY_MTX_FILEPATH, _SURFACES_FILEPATH, _ANALYSIS_GRIDS_FILEPATHS = get_case_files(_CASE_DIRECTORY)
#     surfaces_file = upload_file_to_container(blob_client, _JOB_ID, _SURFACES_FILEPATH)
#     sky_mtx_file = upload_file_to_container(blob_client, _JOB_ID, _SKY_MTX_FILEPATH)
#     analysis_grid_files = [upload_file_to_container(blob_client, _JOB_ID, file_path) for file_path in _ANALYSIS_GRIDS_FILEPATHS]
#
#     print("")
#
#     # Generate batch credentials and client
#     batch_credentials = batchauth.SharedKeyCredentials(_BATCH_ACCOUNT_NAME, _BATCH_ACCOUNT_KEY)
#     batch_client = batch.BatchServiceClient(batch_credentials, base_url=_BATCH_ACCOUNT_URL)
#     print("Batch client generated")
#
#     #################
#     # Create a pool #
#     #################
#
#     # # Tidying up - if the pool already exists
#     # try:
#     #     batch_client.pool.delete(_POOL_ID)
#     #     blob_client.delete_container(_JOB_ID)
#     # except:
#     #     pass
#
#     # Get the node agent SKU and image reference for the virtual machine configuration.
#     sku_to_use, image_ref_to_use = select_latest_verified_vm_image_with_node_agent_sku(batch_client, _NODE_OS_PUBLISHER, _NODE_OS_OFFER, _NODE_OS_SKU)
#
#     # Define the start task for the pool
#     node_start_command = [
#         "sudo touch ./do_i_exist.txt",
#         "sudo cp -p do_i_exist.txt $AZ_BATCH_NODE_SHARED_DIR"
#     ]
#
#     start_task = batchmodels.StartTask(
#         command_line=wrap_commands_in_shell("linux", node_start_command),
#         user_identity=batchmodels.UserIdentity(user_name="yoda", auto_user=batchmodels.AutoUserSpecification(scope=batchmodels.AutoUserScope.pool, elevation_level=batchmodels.ElevationLevel.admin)),
#         wait_for_success=True,
#         resource_files=[]
#     )
#
#     # Define the pool
#     new_pool = batch.models.PoolAddParameter(
#         id=_POOL_ID,
#         virtual_machine_configuration=batchmodels.VirtualMachineConfiguration(
#             image_reference=image_ref_to_use,
#             node_agent_sku_id=sku_to_use
#         ),
#         vm_size=_POOL_VM_SIZE,
#         enable_auto_scale=True,
#         auto_scale_formula='pendingTaskSamplePercent = $PendingTasks.GetSamplePercent(180 * TimeInterval_Second);pendingTaskSamples = pendingTaskSamplePercent < 70 ? 1 : avg($PendingTasks.GetSample(180 * TimeInterval_Second)); $TargetDedicatedNodes = min(100, pendingTaskSamples);',
#         auto_scale_evaluation_interval=datetime.timedelta(minutes=5),
#         start_task=start_task,
#     )
#
#     # Try to create the pool, and tell us why not
#     try:
#         batch_client.pool.add(new_pool)
#     except batchmodels.batch_error.BatchErrorException as err:
#         print_batch_exception(err)
#         raise
#
#     print('[{0:}] pool created'.format(_POOL_ID))
#
#     print('[{0:}] pool created'.format(_POOL_ID))
#
#     print("\n\n\nFinishing ... \n\n\n")
#
#     # # Create a job
#     # batch_client.job.add(job=_JOB_ID)
#     # print('[{}] job created...'.format(_JOB_ID))
#     #
#     #
#     #
#     #
#     #
#     # # Create a bunch of tasks
#     # tasks = []
#     # for n, grid_file in enumerate(analysis_grid_files):
#     #     task_id = 'task_{0:}'.format(re.sub("[^0-9a-zA-Z]", "", grid_file.file_path.replace(".json", "")))
#     #
#     #     resource_files = [
#     #         batchmodels.ResourceFile(file_path="radiance-5.1.0-Linux.tar.gz", blob_source=_RADIANCE_SAS_URL),
#     #         batchmodels.ResourceFile(file_path="lb_hb.tar.gz", blob_source=_LB_HB_SAS_URL),
#     #         batchmodels.ResourceFile(file_path="RunHoneybeeRadiance.py", blob_source=_SCRIPT_SAS_URL),
#     #         batchmodels.ResourceFile(file_path="CopyToBlob.py", blob_source=_COPYTOBLOB_SAS_URL),
#     #         surfaces_file,
#     #         sky_mtx_file,
#     #         grid_file,
#     #     ]
#     #
#     #     task_commands = [
#     #         # Move to the BEST directory!
#     #         "cd",
#     #         "cd /",
#     #         # Set up radiance software
#     #         "sudo cp -p radiance-5.1.0-Linux.tar.gz $AZ_BATCH_NODE_SHARED_DIR",
#     #         "sudo tar xzf radiance-5.1.0-Linux.tar.gz",
#     #         "sudo rsync -av /radiance-5.1.0-Linux/usr/local/radiance/bin/ /usr/local/bin/",
#     #         "sudo rsync -av /radiance-5.1.0-Linux/usr/local/radiance/lib/ /usr/local/lib/ray/",
#     #         # Set up Ladybug tools
#     #         "sudo cp -p lb_hb.tar.gz $AZ_BATCH_NODE_SHARED_DIR",
#     #         "sudo tar xzf lb_hb.tar.gz",
#     #         # Get the script and files to be run
#     #         "sudo cp -p RunHoneybeeRadiance.py $AZ_BATCH_NODE_SHARED_DIR",
#     #         "sudo cp -p CopyToBlob.py $AZ_BATCH_NODE_SHARED_DIR",
#     #         "sudo cp -p surfaces.json $AZ_BATCH_NODE_SHARED_DIR",
#     #         "sudo cp -p sky_mtx.json $AZ_BATCH_NODE_SHARED_DIR",
#     #         "sudo cp -p {0:} $AZ_BATCH_NODE_SHARED_DIR".format(grid_file.file_path),
#     #         # Run the simulation
#     #         "sudo python ./RunHoneybeeRadiance.py -s ./surfaces.json -sm ./sky_mtx.json -p ./{0:}".format(grid_file.file_path),
#     #         # Copy the results back to the blob
#     #         "sudo python CopyToBlob.py -fp {0:} -bn {1:} -sa {2:} -sc {0:} -st {3:}".format(
#     #             grid_file.file_path.replace(".json", "_results.json"),
#     #             _JOB_ID,
#     #             _STORAGE_ACCOUNT_NAME,
#     #             _STORAGE_ACCOUNT_KEY
#     #         )
#     #     ]
#     #
#     #     bash_commands = wrap_commands_in_shell("linux", task_commands)
#     #
#     #     tasks.append(
#     #         batchmodels.TaskAddParameter(
#     #             id=task_id,
#     #             display_name=task_id,
#     #             command_line=bash_commands,
#     #             resource_files=resource_files,
#     #             output_files=[
#     #                 batchmodels.OutputFile(
#     #                     file_pattern="*_result.json",
#     #                     # container=_JOB_ID,
#     #                     # container_url="https://{0:}.blob.core.windows.net/{1:}".format(_STORAGE_ACCOUNT_NAME, _JOB_ID),
#     #                     destination=batchmodels.OutputFileDestination(container=batchmodels.OutputFileBlobContainerDestination(container_url=output_container_sas_url)),
#     #                     upload_options=batchmodels.OutputFileUploadOptions(upload_condition=batchmodels.OutputFileUploadCondition.task_success)
#     #                 )
#     #             ]
#     #         )
#     #     )
#     #
#     # # Add tasks to the batch client
#     # for i in tasks:
#     #     batch_client.task.add(job_id=_JOB_ID, task=i)
#     #
#     # print(tasks)
#
#
