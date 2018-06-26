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

namespace AzureEngine.AzureObjects
{
    public class AzureConnection
    {
        private IAzure azureConnection = null;
        private String azureRegion;
        private String resourceGroup;
        private AzureCredentials credentials = null;

        public AzureConnection(String credentialsFile = null, String resourceGroup = null, String region = null)
        {
            if (credentialsFile == null) throw new NullReferenceException("Please provide a valid credentials file to connecting to Azure");
            if (resourceGroup == null) throw new NullReferenceException("Please provide a valid resource group for this connection with Azure");
            if (region == null) region = "West Europe";

            credentials = SdkContext.AzureCredentialsFactory.FromFile(credentialsFile);

            azureRegion = region;
            this.resourceGroup = resourceGroup;
            azureConnection = Azure.Configure()
                                .WithLogLevel(HttpLoggingDelegatingHandler.Level.Basic)
                                .Authenticate(credentials)
                                .WithDefaultSubscription();
        }

        public IAzure AzureLink { get { return azureConnection; } }
        public String Region { get { return azureRegion; } }
        public String ResourceGroup { get { return resourceGroup; } }
    }
}
