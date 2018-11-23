# call "C:\Users\tgerrish\AppData\Local\Continuum\anaconda3\Scripts\activate.bat" && activate azurebatch

# TODO: Add error handling to delete created pools, containers and jobs if a failure happens somewhere
# TODO - Remove defaults from argParser

import configparser
import datetime
import os
import argparse
import azure.storage.blob as azureblob
import azure.batch.batch_service_client as batch
import azure.batch.batch_auth as batchauth
import azure.batch.models as batchmodels
import common.helpers

if __name__ == '__main__':

    # Obtain arguments from the script inputs
    parser = argparse.ArgumentParser(description="Send Energyplus cases to Azure for simulation")
    parser.add_argument(
        "-d",
        "--caseDirectory",
        type=str,
        help="Path to the case directory from which simulation ingredients are obtained",
        default=os.path.join('resources', 'energyplus_case'))
    parser.add_argument(
        "-c",
        "--configFile",
        type=str,
        help="Path to the azure config file",
        default=os.path.join('common', 'configuration.cfg'))
    parser.add_argument(
        "-id",
        "--projectID",
        type=str,
        help="ID for the job being undertaken",
        default="000000-testproject-3513")
    parser.add_argument(
        "-dp",
        "--deletePool",
        type=str,
        help="Delete pool upon completion?",
        default="no")
    parser.add_argument(
        "-dj",
        "--deleteJob",
        type=str,
        help="Delete job upon completion?",
        default="no")
    parser.add_argument(
        "-dc",
        "--deleteContainer",
        type=str,
        help="Delete container upon completion?",
        default="no")
    args = parser.parse_args()

    # Obtain locations of global configuration and radiance case
    config_file_path = args.configFile
    project_id = args.projectID
    project_id = common.helpers.normalise_string(project_id)+"eplus"
    case_directory = args.caseDirectory

    # Obtain credentials and global variables from the configuration file
    config = configparser.RawConfigParser()
    config.read(config_file_path)

    batch_account_key = config.get('Batch', 'batchaccountkey').replace("%", "%%")
    batch_account_name = config.get('Batch', 'batchaccountname').replace("%", "%%")
    batch_service_url = config.get('Batch', 'batchserviceurl').replace("%", "%%")
    storage_account_key = config.get('Storage', 'storageaccountkey').replace("%", "%%")
    storage_account_name = config.get('Storage', 'storageaccountname').replace("%", "%%")
    storage_account_suffix = config.get('Storage', 'storageaccountsuffix').replace("%", "%%")
    pool_vm_size = config.get('Default', 'poolvmsize')

    # Get the case details from the case_directory
    weatherfile_path = os.path.join(case_directory, "weatherfile.epw")
    model_paths = common.helpers.find_files(os.path.join(case_directory, "models"), ".idf")

    print("\nStarting project [{0:}]".format(project_id))

    # Generate blob client
    block_blob_client = azureblob.BlockBlobService(account_name=storage_account_name, account_key=storage_account_key, endpoint_suffix=storage_account_suffix)

    # Create a blob container for this project
    block_blob_client.create_container(project_id, fail_on_exist=False)

    # Generate a SAS token to pass results back to the container
    container_sas_token = block_blob_client.generate_container_shared_access_signature(project_id, permission=azureblob.ContainerPermissions(read=True, write=True), expiry=datetime.datetime.utcnow() + datetime.timedelta(hours=24), )

    print("\nUploading resource files ...")

    # Upload the weatherfile
    weatherfile = common.helpers.upload_blob_and_create_sas(block_blob_client, project_id, "weatherfile.epw", weatherfile_path, datetime.datetime.utcnow() + datetime.timedelta(days=7))
    print("{0:} uploaded to {1:}/{2:}".format(os.path.basename(weatherfile_path), project_id, "weatherfile.epw"))

    # Upload the analysis grids files
    model_sas_urls = []
    model_names = []
    for model_path in model_paths:
        model_name = common.helpers.normalise_string(os.path.basename(model_path)).replace("idf", ".idf")
        model_sas_urls.append(common.helpers.upload_blob_and_create_sas(block_blob_client, project_id, model_name, model_path, datetime.datetime.utcnow() + datetime.timedelta(days=7)))
        model_names.append(model_name)
        print("{0:} uploaded to {1:}/{2:}".format(os.path.basename(model_name), project_id, model_name))

    # TODO: For some reason with >100 tasks two pools of 100 were created, maybe we just cerate a set of jobs and assign to the same pool?
    # A chunked list of grid indices - to create multiple pool instances
    job_chunks = list(common.helpers.chunks(list(range(0, len(model_names))), 100)) # TODO - change new pool amount

    # Generate batch client
    batch_client = batch.BatchServiceClient(batchauth.SharedKeyCredentials(batch_account_name, batch_account_key), base_url=batch_service_url)

    # Get a verified VM image on which to run the job/s
    sku_to_use, image_ref_to_use = common.helpers.select_latest_verified_vm_image_with_node_agent_sku(batch_client, 'Canonical', 'UbuntuServer', '16.04')

    # Create a pool per job (each job contains a maximum of 100 tasks)
    pool_ids = []
    job_ids = []
    task_ids = []
    for job_n, job_chunk in enumerate(job_chunks):

        print("Job{0:}, containing tasks {1:}".format(job_n, job_chunk))

        pool_id = common.helpers.generate_unique_resource_name("{0:}-pool{1:}".format(project_id, job_n))
        pool_ids.append(pool_id)
        pool_start_commands = ["cd / "]
        pool = batchmodels.PoolAddParameter(
            id=pool_id,
            vm_size=pool_vm_size,
            virtual_machine_configuration=batchmodels.VirtualMachineConfiguration(image_reference=image_ref_to_use, node_agent_sku_id=sku_to_use),
            # target_dedicated_nodes=1,  # for testing with a single file
            # enable_auto_scale=False,  # for testing with a single file
            enable_auto_scale=True,
            auto_scale_formula="pendingTaskSamplePercent = $PendingTasks.GetSamplePercent(180 * TimeInterval_Second); pendingTaskSamples = pendingTaskSamplePercent < 70 ? 1 : avg($PendingTasks.GetSample(180 * TimeInterval_Second)); $TargetDedicatedNodes = min(100, pendingTaskSamples);",
            auto_scale_evaluation_interval=datetime.timedelta(minutes=5),
            max_tasks_per_node=1,
            task_scheduling_policy=batchmodels.TaskSchedulingPolicy(node_fill_type="spread"),
            start_task=batchmodels.StartTask(
                user_identity=batchmodels.UserIdentity(auto_user=batchmodels.AutoUserSpecification(elevation_level=batchmodels.ElevationLevel.admin, scope=batchmodels.AutoUserScope.pool)),
                command_line=common.helpers.wrap_commands_in_shell("linux", pool_start_commands),
                resource_files=[]
            ),
        )
        common.helpers.create_pool_if_not_exist(batch_client, pool)

        # Create job to assign tasks
        job_id = "{0:}-job{1:}".format(pool_id, job_n)
        job_ids.append(job_id)
        job = batchmodels.JobAddParameter(id=job_id, pool_info=batchmodels.PoolInformation(pool_id=pool_id))
        batch_client.job.add(job)
        print("Job created: {0:}".format(job_id))

        # TODO: SOMETHING WRONG WITH THE OUTPUT FILE GENERATION!!!!

        # Create a task per analysis grid
        for n in job_chunk:

            # CHECKING OUTPUT METHOD
            output_file = "{0:}out.csv".format(model_names[n].replace(".idf", ""))
            output_file_node = output_file
            container_sas_url = "https://{0:}.blob.core.windows.net/{1:}?{3:}".format(storage_account_name, project_id, output_file_node, container_sas_token)

            # print("\n##########")
            # print("Output file on node: {0:}".format(output_file_node))
            # print("Container SAS url: {0:}".format(container_sas_url))
            # print("##########\n")
            # CHECKING OUTPUT METHOD

            task_id = "task{0:}".format(n)
            task_ids.append(task_id)
            node_dir = "/mnt/batch/tasks/workitems/{0:}/job-1/{1:}/wd".format(job_id, task_id)

            ####### TESTING ########
            print("RUN COMMAND:")
            print('sudo EnergyPlus -x -r -i "/usr/local/bin/Energy+.idd" -p "{0:}" -w "{2:}/weatherfile.epw" "{2:}/{1:}"'.format(model_names[n].replace(".idf", ""), model_names[n], node_dir))
            print('sudo cp /{0:} {1:}/{0:}'.format(output_file, node_dir))
            ####### TESTING ########

            task_run_commands = [
                "cd /",
                "sudo wget --no-check-certificate https://github.com/NREL/EnergyPlus/releases/download/v8.9.0/EnergyPlus-8.9.0-40101eaafd-Linux-x86_64.sh",
                "sudo chmod +x ./EnergyPlus-8.9.0-40101eaafd-Linux-x86_64.sh",
                'echo "y /usr/local /usr/local/bin" | sudo ./EnergyPlus-8.9.0-40101eaafd-Linux-x86_64.sh',
                'sudo EnergyPlus -x -r -i "/usr/local/bin/Energy+.idd" -p "{0:}" -w "{2:}/weatherfile.epw" "{2:}/{1:}"'.format(model_names[n].replace(".idf", ""), model_names[n], node_dir),
                'sudo cp /{0:} {1:}/{0:}'.format(output_file, node_dir),
                # 'sudo EnergyPlus -x -r -i "/usr/local/bin/Energy+.idd" -d {0:} -p "{1:}" -w "{0:}/weatherfile.epw" "{0:}/{2:}"'.format(node_dir, model_names[n].replace(".idf", ""), model_names[n]),
            ]
            task = batchmodels.TaskAddParameter(
                id=task_id,
                command_line=common.helpers.wrap_commands_in_shell("linux", task_run_commands),
                resource_files=[
                    batchmodels.ResourceFile(file_path=model_names[n], blob_source=model_sas_urls[n]),
                    batchmodels.ResourceFile(file_path="weatherfile.epw", blob_source=weatherfile)],
                output_files=[
                    batchmodels.OutputFile(
                        file_pattern="*out.csv",
                        destination=batchmodels.OutputFileDestination(container=batchmodels.OutputFileBlobContainerDestination(container_url=container_sas_url)),
                        upload_options=batchmodels.OutputFileUploadOptions(upload_condition="taskCompletion"))
                ],
                user_identity=batchmodels.UserIdentity(auto_user=batchmodels.AutoUserSpecification(elevation_level=batchmodels.ElevationLevel.admin, scope=batchmodels.AutoUserScope.task)))
            batch_client.task.add(job_id=job_id, task=task)
            print("Task created: {0:} and assigned to {1:}".format(task_id, job_id))

    # Wait for tasks to complete
    for job_id in job_ids:
        common.helpers.wait_for_tasks_to_complete(batch_client, job_id, datetime.timedelta(hours=4))
    # # Get a list of all the tasks currently running and wait for them to all complete
    # all_tasks = []
    # for job_id in job_ids:
    #     tasks_temp = batch_client.task.list(job_id)
    #     for task_temp in tasks_temp:
    #         all_tasks.append(task_temp)
    # common.helpers.wait_for_tasks_to_complete2(batch_client, all_tasks, datetime.timedelta(minutes=45))
    print("All tasks complete\n")

    # Download the results to the case directory
    if not os.path.exists(os.path.join(case_directory, "Results")):
        os.makedirs(os.path.join(case_directory, "Results"))
    for n in range(len(model_names)):
        output_file = "{0:}out.csv".format(model_names[n].replace(".idf", ""))
        common.helpers.download_blob_from_container(block_blob_client, project_id, output_file, os.path.join(case_directory, "Results"))

    # TODO: I may need to add a sleep here, possibly not depending on how good the download function is

    if args.deleteJob:
        for i in job_ids:
            print("Deleting job: {0:}".format(i))
            batch_client.job.delete(i)
    if args.deletePool:
        for i in pool_ids:
            print("Deleting pool/s: {0:}".format(i))
            batch_client.pool.delete(i)

    # Tidy up the pools, jobs and tasks
    if args.deleteContainer == "yes":
        print("Deleting container: {0:}".format(project_id))
        block_blob_client.delete_container(project_id, fail_not_exist=False)
