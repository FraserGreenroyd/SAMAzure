using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

using AzureEngine.AzureObjects;

namespace AzureEngine
{
    public class AzureEngine
    {
        //This file will contain the engine configurations for communicating with Azure
        private SystemMessageContainer messageContainer;

        private AzureConnection azureConnection = null;
        private VirtualMachine virtualMachine = null;
        private BlobStorage blobStorage = null;
        private AzureBatchClient batchClient = null;

        public AzureEngine(SystemMessageContainer container = null)
        {
            messageContainer = (container == null ? new SystemMessageContainer() : container);
        }

        public void CreateAzureConnection(String credentialsFile, String resourceGroup, String region)
        {
            messageContainer.AddInformationMessage("Creating connection to Azure...");
            azureConnection = new AzureConnection(credentialsFile, resourceGroup, region);
            CreateResourceGroupIfNotExists(resourceGroup);
            messageContainer.AddInformationMessage("Connection to Azure created...");
        }

        public void CreateVirtualMachine()
        {
            messageContainer.AddInformationMessage("Creating VM instance...");
            virtualMachine = new VirtualMachine(azureConnection, messageContainer);
            messageContainer.AddInformationMessage("VM Instance created...");
        }

        public void CreateBlobStorage(String blobConnectionString)
        {
            messageContainer.AddInformationMessage("Creating blob storage...");
            blobStorage = new BlobStorage(blobConnectionString, messageContainer);
            messageContainer.AddInformationMessage("Blob storage created...");
        }

        public void CreateBatchClient(String accountName, String accountKey, String accountURL, String poolID, String jobID, int poolNodeCount, String poolVMSize)
        {
            messageContainer.AddInformationMessage("Creating batch client...");
            batchClient = new AzureBatchClient(accountName, accountKey, accountURL, blobStorage, poolID, jobID, poolNodeCount, poolVMSize);
            messageContainer.AddInformationMessage("Batch client created...");
        }

        private void CreateResourceGroupIfNotExists(String resourceGroupName)
        {
            if (azureConnection == null)
            {
                messageContainer.AddErrorMessage("The Azure component has not been initialised");
                return;
            }

            if(!azureConnection.AzureLink.ResourceGroups.Contain(resourceGroupName))
                azureConnection.AzureLink.ResourceGroups.Define(resourceGroupName).WithRegion(azureConnection.Region).Create();
        }

        public void SpinUpVM()
        {
            messageContainer.AddInformationMessage("Spinning up Virtual Machine... Please wait...");
            virtualMachine.CreateVM();
            messageContainer.AddStatusMessage("VM set up - some stats are below");
            foreach (String s in virtualMachine.Details())
                messageContainer.AddInformationMessage(s);
        }

        public void DeallocateVM()
        {
            if (virtualMachine != null)
                virtualMachine.DeallocateVM();
        }

        public void DeleteResourceGroup()
        {
            azureConnection.AzureLink.ResourceGroups.DeleteByName(azureConnection.ResourceGroup);
        }

        public void SwitchOff()
        {
            virtualMachine.SwitchOffVM();
        }

        public void AddTask(String command, String fileName = null)
        {
            batchClient.AddTask(command, blobStorage.GenerateResourceFile(fileName));
        }

        public void MoveCompletedTaskFiles()
        {
            if(batchClient.AwaitTaskCompletion())
            {
                messageContainer.AddInformationMessage("Tasks completed apparently...");
            }
        }

        public async Task SendFile(String filePath, String fileName)
        {
            await blobStorage.SendFile(filePath, fileName);
        }
    }
}
