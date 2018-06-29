using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

using Microsoft.Azure.Management.Compute.Fluent;
using Microsoft.Azure.Management.Compute.Fluent.Models;
using Microsoft.Azure.Management.Fluent;
using Microsoft.Azure.Management.ResourceManager.Fluent;
using Microsoft.Azure.Management.ResourceManager.Fluent.Core;

using Microsoft.Azure.Management.ResourceManager.Fluent.Authentication;

using AzureEngine.Utilities;

namespace AzureEngine.AzureObjects
{
    public class AzureConnection
    {
        private IAzure azureConnection = null;
        private SystemMessageContainer messageContainer = null;

        public AzureConnection(String credentialsFile = null, SystemMessageContainer messageContainer = null)
        {
            if (credentialsFile == null) throw new NullReferenceException("Please provide a valid credentials file to connecting to Azure");

            azureConnection = Azure.Configure()
                                .WithLogLevel(HttpLoggingDelegatingHandler.Level.Basic)
                                .Authenticate(SdkContext.AzureCredentialsFactory.FromFile(credentialsFile))
                                .WithDefaultSubscription();

            this.messageContainer = (messageContainer == null ? new SystemMessageContainer() : messageContainer);

            CreateResourceGroupIfNotExists();
        }

        private void CreateResourceGroupIfNotExists()
        {
            if (!azureConnection.ResourceGroups.Contain(AzureConnectionUtility.ResourceGroup))
            {
                messageContainer.AddInformationMessage("Creating resource group with name - " + AzureConnectionUtility.ResourceGroup + " ...");
                azureConnection.ResourceGroups.Define(AzureConnectionUtility.ResourceGroup).WithRegion(AzureConnectionUtility.Region).Create();
                messageContainer.AddStatusMessage("Resource Group (" + AzureConnectionUtility.ResourceGroup + ") created...");
            }
        }

        public IAzure AzureLink { get { return azureConnection; } }
    }
}
