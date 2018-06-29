using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

using Microsoft.Azure.Batch;
using Microsoft.Azure.Batch.Auth;
using Microsoft.Azure.Batch.Common;

using Microsoft.Azure.Batch.Conventions.Files;

using Microsoft.WindowsAzure.Storage.Blob;

using AzureEngine.Utilities;

namespace AzureEngine.AzureObjects
{
    public class AzureBatchClient
    {
        //Batch account credentials
        private String batchAccountName = null;
        private String batchAccountKey = null;
        private String batchAccountURL = null;

        private BlobStorage blobStorage = null;
        private SystemMessageContainer messageContainer = null;

        //Batch client
        private BatchClient batchClient = null;

        //Pool, Job, and Task data
        CloudPool pool = null;
        CloudJob job = null;

        public AzureBatchClient(String accountName = null, String accountKey = null, String accountURL = null, BlobStorage storage = null, String poolID = null, String jobID = null, int poolNodeCount = 2, String poolVMSize = null, SystemMessageContainer container = null)
        {
            if (accountName == null) throw new NullReferenceException("Please provide a valid batch account name");
            if (accountKey == null) throw new NullReferenceException("Please provide a valid batch account key");
            if (accountURL == null) throw new NullReferenceException("Please provide a valid batch account URL");
            if (storage == null) throw new NullReferenceException("Please provide a valid blob storange reference");

            batchAccountName = accountName;
            batchAccountKey = accountKey;
            batchAccountURL = accountURL;
            blobStorage = storage;

            poolID = (poolID == null ? AzureConnectionUtility.BuildProjectNameReference() + "-pool" : poolID);
            jobID = (jobID == null ? AzureConnectionUtility.BuildProjectNameReference() + "-job" : jobID);
            poolVMSize = (poolVMSize == null ? "Basic_A1" : poolVMSize);

            messageContainer = (container == null ? new SystemMessageContainer() : container);

            messageContainer.AddInformationMessage("Creating batch client...");

            batchClient = BatchClient.Open(new BatchSharedKeyCredentials(batchAccountURL, batchAccountName, batchAccountKey));
            messageContainer.AddInformationMessage("Batch client created...");

            //Create the pool if it doesn't exist
            pool = CreatePoolIfNotExists(poolID, poolVMSize, poolNodeCount);
            job = CreateJobIfNotExists(jobID, pool.Id);
        }

        public void AddTask(String command = null, List<ResourceFile> resourceFiles = null)
        {
            //if (resourceFile == null) throw new NullReferenceException("Please provide a valid resource file for this task to operate on");
            if (command == null) throw new NullReferenceException("Please provide a command for this task to run");

            CloudTask task = new CloudTask(Guid.NewGuid().ToString(), command);
            if (resourceFiles != null && resourceFiles.Count > 0)
                task.ResourceFiles = resourceFiles;

            String perm = blobStorage.Container.GetSharedAccessSignature(new SharedAccessBlobPolicy()
            {
                Permissions = SharedAccessBlobPermissions.Write,
                SharedAccessExpiryTime = DateTimeOffset.UtcNow.AddDays(1)
            });

            String containerUrl = blobStorage.Container.Uri.AbsoluteUri + perm;

            task.OutputFiles = new List<OutputFile> {
                        new OutputFile( @"output.txt",
                                            new OutputFileDestination(
                                                new OutputFileBlobContainerDestination(containerUrl, task.Id + @"\output.txt")),
                                            new OutputFileUploadOptions(OutputFileUploadCondition.TaskCompletion)),

                        new OutputFile(
                                filePattern: @"output.txt",
                                destination: new OutputFileDestination(new OutputFileBlobContainerDestination(
                                    containerUrl: containerUrl,
                                    path: task.Id + @"\output.txt")),
                                uploadOptions: new OutputFileUploadOptions(
                                    uploadCondition: OutputFileUploadCondition.TaskCompletion)),

            };

            task.UserIdentity = new UserIdentity(
                        new AutoUserSpecification(
                            scope: AutoUserScope.Task,
                            elevationLevel: ElevationLevel.Admin
                        )
                    );

            batchClient.JobOperations.AddTask(job.Id, task);
        }

        private CloudJob CreateJobIfNotExists(String jobID, String poolID)
        {
            messageContainer.AddInformationMessage("Configuring job...");

            CloudJob cJob = null;
            try { cJob = batchClient.JobOperations.GetJob(jobID); } catch { }

            if(cJob == null)
            {
                messageContainer.AddInformationMessage("Creating job...");
                cJob = batchClient.JobOperations.CreateJob();
                cJob.Id = jobID;
                cJob.PoolInformation = new PoolInformation { PoolId = poolID };
                
                cJob.Commit();
                messageContainer.AddInformationMessage("Job created...");
            }
            messageContainer.AddInformationMessage("Job configured...");

            return cJob;
        }

        private CloudPool CreatePoolIfNotExists(String poolID, String vmSize, int computerNodes = 2, ImageReference imageReference = null)
        {
            messageContainer.AddInformationMessage("Configuring pool...");
            CloudPool cPool = null;
            try { cPool = batchClient.PoolOperations.GetPool(poolID); } catch { }

            if (cPool == null)
            {
                imageReference = (imageReference == null ? CreateImageReference() : imageReference);
                VirtualMachineConfiguration vmConfig = new VirtualMachineConfiguration(imageReference, SKUReference(imageReference.Offer));

                messageContainer.AddInformationMessage("Creating pool...");
                cPool = batchClient.PoolOperations.CreatePool(poolID, vmSize, vmConfig, computerNodes);
               /* if(cPool.StartTask == null)
                    cPool.StartTask = new StartTask();

                cPool.StartTask.UserIdentity = new UserIdentity(
                        new AutoUserSpecification(
                            scope: AutoUserScope.Pool,
                            elevationLevel: ElevationLevel.Admin
                        )
                    );*/
                cPool.Commit();
                messageContainer.AddInformationMessage("Pool created...");
            }

            messageContainer.AddInformationMessage("Pool configured...");

            return cPool;
        }

        private ImageReference CreateImageReference(String publisher = null, String offer = null, String sku = null, String version = null)
        {
            publisher = (publisher == null ? "Canonical" : publisher);
            offer = (offer == null ? "UbuntuServer" : offer);
            sku = (sku == null ? "16.04-LTS" : sku);
            version = (version == null ? "latest" : version);

            return new ImageReference(offer, publisher, sku, version);
        }

        private String SKUReference(String offer)
        {
            if (offer.Contains("Ubuntu"))
                return "batch.node.ubuntu 16.04";
            else if (offer.Contains("Windows"))
                return "batch.node.windows amd64";

            //Add more as necessary
            return "";
        }

        public bool AwaitTaskCompletion()
        {
            TimeSpan timeout = TimeSpan.FromMinutes(30);
            batchClient.Utilities.CreateTaskStateMonitor().WaitAll(batchClient.JobOperations.ListTasks(job.Id), TaskState.Completed, timeout);

            return true;
        }

        public void MoveCompletedTaskResults()
        {
            List<CloudTask> completedTasks = GetCompletedTasks();

            foreach(CloudTask ct in completedTasks)
            {
                //NodeFile file = ct.GetNodeFile(ct.Id + @"\Output.txt");
                //blobStorage.SendFile(file.Path, file.Name);
            }
        }

        private List<CloudTask> GetCompletedTasks()
        {
            return batchClient.JobOperations.ListTasks(job.Id).ToList();
        }

        public void InstallEnergyPlus(String epCommand)
        {
            //Run the automatic script for installing EnergyPlus on the machine
            messageContainer.AddInformationMessage("Starting installation of EnergyPlus on batch " + batchClient.ToString() + "...");
            AddTask(epCommand);
            if (AwaitTaskCompletion())
                messageContainer.AddInformationMessage("EnergyPlus successfully installed...");
        }
    }
}
