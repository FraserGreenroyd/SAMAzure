# call "C:\Users\tgerrish\AppData\Local\Continuum\anaconda2\Scripts\activate.bat" && activate azurebatch

# from __future__ import print_function
import configparser
# try:
#     import configparser
# except ImportError:
#     import ConfigParser as configparser

import datetime
import os
import argparse
import re  # for file renaming
import azure.storage.blob as azureblob
import azure.batch.batch_service_client as batch
import azure.batch.batch_auth as batchauth
import azure.batch.models as batchmodels
import common.helpers

if __name__ == '__main__':

    print("###############################")
    print("########### START #############")

    # Obtain arguments from the script inputs
    parser = argparse.ArgumentParser(description="Send Radiance case to Azure for simulation")
    parser.add_argument(
        "-d",
        "--caseDirectory",
        type=str,
        help="Path to the case directory from which simulation ingredients are obtained",
        default=os.path.join('resources', 'radiance_case'))  # TODO - Remove post testing
    parser.add_argument(
        "-c",
        "--configFile",
        type=str,
        help="Path to the azure config file",
        default=os.path.join('common', 'configuration.cfg'))  # TODO - Remove post testing
    parser.add_argument(
        "-id",
        "--caseID",
        type=str,
        help="ID for the job being undertaken",
        default="000000-testproject-3513")  # TODO - Remove post testing
    parser.add_argument(
        "-dp",
        "--deletePool",
        type=str,
        help="Delete pool upon completion?",
        default="yes")  # TODO - Refactor post testing
    parser.add_argument(
        "-dj",
        "--deleteJob",
        type=str,
        help="Delete job upon completion?",
        default="yes")  # TODO - Refactor post testing
    parser.add_argument(
        "-dc",
        "--deleteContainer",
        type=str,
        help="Delete container upon completion?",
        default="no")  # TODO - Refactor post testing

    args = parser.parse_args()

    # Obtain locations of global configuration and radiance case
    _CONFIGURATION_PATH = args.configFile
    _CONTAINER_NAME = args.caseID
    _CONTAINER_NAME = common.helpers.normalise_string(_CONTAINER_NAME)
    _RADIANCE_CASE_PATH = args.caseDirectory

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
    # should_delete_container = config.getboolean('Default', 'shoulddeletecontainer')
    # should_delete_job = config.getboolean('Default', 'shoulddeletejob')
    # should_delete_pool = config.getboolean('Default', 'shoulddeletepool')
    pool_vm_size = config.get('Default', 'poolvmsize')
    # pool_vm_count = config.getint('Default', 'poolvmcount')

    # Generate blob client
    block_blob_client = azureblob.BlockBlobService(account_name=storage_account_name, account_key=storage_account_key, endpoint_suffix=storage_account_suffix)
    print("Block blob client generated: {0:}".format(block_blob_client))

    # Create a blob container for this project
    block_blob_client.create_container(_CONTAINER_NAME, fail_on_exist=False)
    print("Container created: {0:}".format(_CONTAINER_NAME))

    # Generate a SAS token to pass results back to the container
    container_sas_token = block_blob_client.generate_container_shared_access_signature(_CONTAINER_NAME, permission=azureblob.ContainerPermissions(read=True, write=True), expiry=datetime.datetime.utcnow() + datetime.timedelta(minutes=30),)
    print("Container SAS token generated: {0:}".format(container_sas_token))

    print("")
    print("Uploading resource files ...")

    # Upload the context surfaces file
    surfaces_sas_url = common.helpers.upload_blob_and_create_sas(block_blob_client, _CONTAINER_NAME, "surfaces.json", _SURFACES_PATH, datetime.datetime.utcnow() + datetime.timedelta(days=7))
    print("{0:} uploaded to {1:}/{2:}".format(os.path.basename(_SURFACES_PATH), _CONTAINER_NAME, "surfaces.json"))

    # Upload the sky matrix file
    sky_mtx_sas_url = common.helpers.upload_blob_and_create_sas(block_blob_client, _CONTAINER_NAME, "sky_mtx.json", _SKY_MTX_PATH, datetime.datetime.utcnow() + datetime.timedelta(days=7))
    print("{0:} uploaded to {1:}/{2:}".format(os.path.basename(_SKY_MTX_PATH), _CONTAINER_NAME, "sky_mtx.json"))

    # Upload the analysis grids files
    analysis_grid_sas_urls = []
    analysis_grid_names = []
    for _GRID_FILE in _ANALYSIS_GRID_PATHS:
        _GRID_NAME = common.helpers.normalise_string(os.path.basename(_GRID_FILE)).replace("json", ".json")
        analysis_grid_sas_urls.append(common.helpers.upload_blob_and_create_sas(block_blob_client, _CONTAINER_NAME, _GRID_NAME, _GRID_FILE, datetime.datetime.utcnow() + datetime.timedelta(days=7)))
        analysis_grid_names.append(_GRID_NAME)
        print("{0:} uploaded to {1:}/{2:}".format(os.path.basename(_GRID_NAME), _CONTAINER_NAME, _GRID_NAME))

    # The number of grids to be processed
    n_tasks = len(analysis_grid_names)

    # A chunked list of grid indices - to create multiple pool instances
    task_chunks = list(common.helpers.chunks(list(range(0, n_tasks)), 100))

    # MAJOR TODO!!!!
    # TODO - Add autoscaling for pools! - 100 tasks per job, 1 job per node create a pool per job!

    # Generate batch client
    batch_client = batch.BatchServiceClient(batchauth.SharedKeyCredentials(batch_account_name, batch_account_key), base_url=batch_service_url)
    # print("Batch client generated: {0:}".format(batch_client))

    # Get a verified VM image on which to run the job/s
    sku_to_use, image_ref_to_use = common.helpers.select_latest_verified_vm_image_with_node_agent_sku(batch_client, 'Canonical', 'UbuntuServer', '16.04')

    # Create pool
    pool_id = common.helpers.generate_unique_resource_name("{0:}-pool".format(_CONTAINER_NAME))
    pool_start_commands = ["cd / "]
    pool = batchmodels.PoolAddParameter(
        id=pool_id,
        vm_size=pool_vm_size,
        virtual_machine_configuration=batchmodels.VirtualMachineConfiguration( image_reference=image_ref_to_use, node_agent_sku_id=sku_to_use),
        # target_dedicated_nodes=n_tasks,
        enable_auto_scale=True,
        auto_scale_formula="pendingTaskSamplePercent = $PendingTasks.GetSamplePercent(180 * TimeInterval_Second); pendingTaskSamples = pendingTaskSamplePercent < 70 ? 1 : avg($PendingTasks.GetSample(180 * TimeInterval_Second)); $TargetDedicatedNodes = min(100, pendingTaskSamples);",
        auto_scale_evaluation_interval=datetime.timedelta(minutes=5),
        start_task=batchmodels.StartTask(
            user_identity=batchmodels.UserIdentity(auto_user=batchmodels.AutoUserSpecification(elevation_level=batchmodels.ElevationLevel.admin, scope=batchmodels.AutoUserScope.pool)),
            command_line=common.helpers.wrap_commands_in_shell("linux", pool_start_commands),
            resource_files=[]
        ),
    )
    common.helpers.create_pool_if_not_exist(batch_client, pool)

    # Create job to assign tasks
    job_id = "{0:}-job".format(pool_id)
    job = batchmodels.JobAddParameter(id=job_id, pool_info=batchmodels.PoolInformation(pool_id=pool_id))
    batch_client.job.add(job)
    print("Job created: {0:}".format(job_id))

    # Create a task per analysis grid
    for n in range(len(analysis_grid_names)):
        task_id = "{0:}-task{1:}".format(job_id, n)
        node_dir = "./mnt/batch/tasks/workitems/{0:}/job-1/{1:}/wd".format(job_id, task_id)
        output_file = analysis_grid_names[n].replace(".json", "_result.json")
        task_run_commands = [
            "cd /",
            "sudo wget --no-check-certificate https://github.com/FraserGreenroyd/SAMAzure/raw/master/TestFiles/resources/azure_common/CopyToBlob.py",
            "sudo wget --no-check-certificate https://github.com/FraserGreenroyd/SAMAzure/raw/master/TestFiles/resources/azure_common/radiance-5.1.0-Linux.tar.gz",
            "sudo tar xzf radiance-5.1.0-Linux.tar.gz",
            "sudo rsync -av /radiance-5.1.0-Linux/usr/local/radiance/bin/ /usr/local/bin/",
            "sudo rsync -av /radiance-5.1.0-Linux/usr/local/radiance/lib/ /usr/local/lib/ray/",
            "sudo wget --no-check-certificate https://github.com/FraserGreenroyd/SAMAzure/raw/master/TestFiles/resources/azure_common/lb_hb.tar.gz",
            "sudo tar xzf lb_hb.tar.gz",
            "sudo wget --no-check-certificate https://github.com/FraserGreenroyd/SAMAzure/raw/master/TestFiles/resources/azure_common/RunHoneybeeRadiance.py",
            "sudo python RunHoneybeeRadiance.py -s {0:}/surfaces.json -sm {0:}/sky_mtx.json -p {0:}/{1:}".format(node_dir, analysis_grid_names[n]),
        ]
        task = batchmodels.TaskAddParameter(
            id=task_id,
            command_line=common.helpers.wrap_commands_in_shell("linux", task_run_commands),
            resource_files=[
                batchmodels.ResourceFile(file_path=analysis_grid_names[n], blob_source=analysis_grid_sas_urls[n]),
                batchmodels.ResourceFile(file_path="sky_mtx.json", blob_source=sky_mtx_sas_url),
                batchmodels.ResourceFile(file_path="surfaces.json", blob_source=surfaces_sas_url)],
            output_files=[
                batchmodels.OutputFile(
                    file_pattern="*_result.json",
                    destination=batchmodels.OutputFileDestination(
                        container=batchmodels.OutputFileBlobContainerDestination(
                            container_url="https://{0:}.blob.core.windows.net/{1:}?{3:}".format(storage_account_name, _CONTAINER_NAME, os.path.join("Results", output_file), container_sas_token))),
                    upload_options=batchmodels.OutputFileUploadOptions(upload_condition="taskCompletion")
                )
            ],
            user_identity=batchmodels.UserIdentity(auto_user=batchmodels.AutoUserSpecification(elevation_level=batchmodels.ElevationLevel.admin, scope=batchmodels.AutoUserScope.task)))
        batch_client.task.add(job_id=job_id, task=task)
        print("Task created: {0:}".format(task_id))

    common.helpers.wait_for_tasks_to_complete(batch_client, job_id, datetime.timedelta(minutes=45))
    # print("Adding task/s")
    # tasks = batch_client.task.list(job_id)
    # task_ids = [task.id for task in tasks]
    # common.helpers.print_task_output(batch_client, job_id, task_ids)
    print("All tasks complete")

    if args.deleteJob:
        print("Deleting job: {0:}".format(job_id))
    batch_client.job.delete(job_id)
    if args.deletePool:
        print("Deleting pool: {0:}".format(pool_id))
        batch_client.pool.delete(pool_id)

    # Download the results to the case directory
    if not os.path.exists(os.path.join(_RADIANCE_CASE_PATH, "Results")):
        os.makedirs(os.path.join(_RADIANCE_CASE_PATH, "Results"))
    for n in range(len(analysis_grid_names)):
        output_file = analysis_grid_names[n].replace(".json", "_result.json")
        common.helpers.download_blob_from_container(block_blob_client, _CONTAINER_NAME, output_file, os.path.join(_RADIANCE_CASE_PATH, "Results"))

    # Tidy up the pools, jobs and tasks
    if args.deleteContainer == "yes":
        print("Deleting container: {0:}".format(_CONTAINER_NAME))
        block_blob_client.delete_container(_CONTAINER_NAME, fail_not_exist=False)
