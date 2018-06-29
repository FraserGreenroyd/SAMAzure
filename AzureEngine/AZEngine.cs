using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

using AzureEngine.AzureObjects;

using Microsoft.Azure.Batch;

using AzureEngine.Utilities;

namespace AzureEngine
{
    public class AZEngine
    {
        private SystemMessageContainer messageContainer = null;

        private AzureConnection azureConnection = null;
        private VirtualMachine virtualMachineContainer = null;
        private BlobStorage blobContainer = null;
        private List<AzureBatchClient> batchContainer = null;

        public AZEngine(String projectNumber, String projectName, String credentialsFile = null, String resourceGroup = null, String region = null, String blobConnectionString = null, String batchAccountName = null, String batchAccountKey = null, String batchAccountURL = null, String poolVMSize = null)
        {
            if (projectNumber == null || projectNumber == "") throw new NullReferenceException("Please provide a valid project number to create an Azure connection");
            if (projectName == null || projectName == "") throw new NullReferenceException("Please provide a valid project name to create an Azure connection");
            AzureConnectionUtility.ProjectNumber = projectNumber;
            AzureConnectionUtility.ProjectName = projectName;

            messageContainer = new SystemMessageContainer();
            messageContainer.MessagesUpdated += MessageContainer_MessagesUpdated;

            if (credentialsFile != null) AzureConnectionUtility.CredentialsFile = credentialsFile;
            if (resourceGroup != null) AzureConnectionUtility.ResourceGroup = resourceGroup;
            if (region != null) AzureConnectionUtility.Region = region;
            if (blobConnectionString != null) AzureConnectionUtility.BlobConnectionString = blobConnectionString;
            if (batchAccountName != null) AzureConnectionUtility.BatchAccountName = batchAccountName;
            if (batchAccountKey != null) AzureConnectionUtility.BatchAccountKey = batchAccountKey;
            if (batchAccountURL != null) AzureConnectionUtility.BatchAccountURL = batchAccountURL;
            if (poolVMSize != null) AzureConnectionUtility.PoolVMSize = poolVMSize;

            batchContainer = new List<AzureBatchClient>();

            CreateAzureConnection(); //Create the connection to Azure on creation as we will want this for pretty much everything else
        }

        public void CreateAzureConnection()
        {
            messageContainer.AddInformationMessage("Creating connection to Azure...");
            azureConnection = new AzureConnection(AzureConnectionUtility.CredentialsFile);
            messageContainer.AddStatusMessage("Connection to Azure established!");
        }

        public void CreateVirtualMachine()
        {
            if (azureConnection == null) throw new NullReferenceException("Please ensure a connection to Azure exists first...");

            messageContainer.AddInformationMessage("Creating VM instance...");
            virtualMachineContainer = new VirtualMachine(azureConnection, messageContainer);
            messageContainer.AddStatusMessage("VM instance has been created!");
        }

        public async Task CreateBlobStorage()
        {
            messageContainer.AddInformationMessage("Creating blob storage connection...");
            blobContainer = new BlobStorage(AzureConnectionUtility.BlobConnectionString, messageContainer);
            await blobContainer.CreateBlobStorage(AzureConnectionUtility.BuildProjectNameReference());
            messageContainer.AddStatusMessage("Blob container created!");
        }

        public void CreateBatchClients(int filesToRun)
        {
            messageContainer.AddInformationMessage("Creating batch client(s)...");

            //Each batch pool can only have 100 nodes, and we want to use one node per file. If we have more than 100 nodes we need to create more than one batch client
            int maxClients = (int)Math.Ceiling((double)filesToRun/ 100);
            int numberOfFullNodes = (int)Math.Floor((double)filesToRun / 100);

            for(int x = 0; x < maxClients; x++)
            {
                //Create a new batch client with the pool size either 100 or max files
                int numNodes = (int)(x < numberOfFullNodes ? 100 : filesToRun % 100);
                AzureBatchClient client = new AzureBatchClient(AzureConnectionUtility.BatchAccountName, AzureConnectionUtility.BatchAccountKey, AzureConnectionUtility.BatchAccountURL, blobContainer, AzureConnectionUtility.BuildProjectNameReference() + x.ToString(), AzureConnectionUtility.BuildProjectNameReference(), numNodes, AzureConnectionUtility.PoolVMSize, messageContainer);

                batchContainer.Add(client);
            }

            messageContainer.AddStatusMessage(maxClients + " Batch Clients created!");
        }

        public void InstallEnergyPlus()
        {
            messageContainer.AddInformationMessage("Installing EnergyPlus on all Batch Clients");
            foreach (AzureBatchClient client in batchContainer)
                client.InstallEnergyPlus(EnergyPlusUtility.CompileEPInstallCommand());

            messageContainer.AddStatusMessage("EnergyPlus successfully installed on all Batch Clients!");
        }

        public async Task UploadFile(String fileToUploadToBlob)
        {
            await UploadFiles(new List<string> { fileToUploadToBlob });
        }

        public async Task UploadFiles(List<String> filesToUploadToBlob)
        {
            if (blobContainer == null) throw new NullReferenceException("Please ensure the blob storage is correctly connected before uploading files");

            foreach (String s in filesToUploadToBlob)
                await blobContainer.SendFile(System.IO.Path.GetDirectoryName(s) + @"\", System.IO.Path.GetFileName(s));
        }

        public void RunEnergyPlus(List<String> filesToTask, String epwFile)
        {
            epwFile = System.IO.Path.GetFileName(epwFile); //Protection in case the epwFile is a full path

            String mainCommand = "\"/usr/local/EnergyPlus-8-8-0/energyplus-8.8.0\" -a -x -r -w \"" + epwFile + "\" \" "; //Main command - add the file to task after
            // ep2.idf\"";

            for(int x = 0; x < filesToTask.Count; x++)
            {
                String file = System.IO.Path.GetFileName(filesToTask[x]);
                String fullCommand = mainCommand + file + "\"";

                int batchIndex = (int)Math.Floor((double)x / 100);

                batchContainer[batchIndex].AddTask(fullCommand, new List<ResourceFile> { blobContainer.GenerateResourceFile(file) });
            }         
        }

        public bool TrueWhenTasksComplete()
        {
            bool allDone = true;

            foreach (AzureBatchClient client in batchContainer)
                allDone &= client.AwaitTaskCompletion();

            return allDone;
        }

        private void MessageContainer_MessagesUpdated(object sender, System.ComponentModel.PropertyChangedEventArgs e)
        {
            //Write the output to a file
            if (!System.IO.File.Exists(@"C:\Users\fgreenro\Documents\Repo Code\Test Files & Scripts\AzureTestOutput.txt"))
                System.IO.File.Create(@"C:\Users\fgreenro\Documents\Repo Code\Test Files & Scripts\AzureTestOutput.txt");

            try
            {
                System.IO.StreamWriter sw = new System.IO.StreamWriter(@"C:\Users\fgreenro\Documents\Repo Code\Test Files & Scripts\AzureTestOutput.txt", true);
                SystemMessage sm = messageContainer.GetLatestMessage();
                sw.WriteLine(sm.TimeStamp + ": " + sm.GetType() + sm.Message);
                if (sm.Type == SystemMessage.MessageType.Error)
                    sw.WriteLine(sm.ErrorDetails);

                sw.Close();
            }
            catch { }
        }
    }
}
