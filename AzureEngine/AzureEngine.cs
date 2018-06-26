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

        public AzureEngine(String credentialsFile, String resourceGroup, String region, SystemMessageContainer container = null)
        {
            messageContainer = (container == null ? new SystemMessageContainer() : container);

            azureConnection = new AzureConnection(credentialsFile, resourceGroup, region);
            virtualMachine = new VirtualMachine(azureConnection, container);

            CreateResourceGroupIfNotExists(resourceGroup);
        }

        public AzureEngine(SystemMessageContainer container)
        {
            messageContainer = container;
        }

        private void CreateResourceGroupIfNotExists(String resourceGroupName)
        {
            if (azureConnection == null) throw new NullReferenceException("The Azure component has not been initialised");

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
    }
}
