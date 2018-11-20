using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace AzureEngine.Utilities
{
    public static class AzureConnectionUtility
    {
        private static String credentialsFile = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData) + @"\Grasshopper\Libraries\Azure\azureauth.properties";
        public static String CredentialsFile { get { return credentialsFile; } set { credentialsFile = value; } }

        private static String resourceGroup = "BH_SAP_Cloud_Compute";
        public static String ResourceGroup { get { return resourceGroup; } set { resourceGroup = value; } }

        private static String region = "West Europe";
        public static String Region { get { return region; } set { region = value; } }

        private static String blobConnectionString = @"DefaultEndpointsProtocol=https;AccountName=bhsapcloudblob;AccountKey=hgHFJty3ffGZAXVon6zwIneiW1xv95K0Av5lPuY20lz8kCOUBEgyikZt9GKaC3k1+GNwcR2LsbG6kHPeZ9NVgg==;EndpointSuffix=core.windows.net";
        public static String BlobConnectionString { get { return blobConnectionString; } set { blobConnectionString = value; } }

        private static String batchAccountName = "bhsapcloudbatch3513";
        public static String BatchAccountName { get { return batchAccountName; } set { batchAccountName = value; } }

        private static String batchAccountKey = @"";
        public static String BatchAccountKey { get { return batchAccountKey; } set { batchAccountKey = value; } }

        private static String batchAccountURL = "https://bhsapcloudbatch3513.westeurope.batch.azure.com";
        public static String BatchAccountURL { get { return batchAccountURL; } set { batchAccountURL = value; } }

        private static String poolVMSize = "Basic_A1";
        public static String PoolVMSize { get { return poolVMSize; } set { poolVMSize = value; } }

        private static String projectNumber = "";
        public static String ProjectNumber { get { return projectNumber; } set { projectNumber = value; } }

        private static String projectName = "";
        public static String ProjectName { get { return projectName; } set { projectName = value; } }

        public static String BuildProjectNameReference()
        {
            return projectNumber + "-" + projectName.Replace(" ", "").ToLower() + "-3513";
        }
    }
}
