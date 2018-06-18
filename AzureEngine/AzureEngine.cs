using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

using Microsoft.WindowsAzure.Storage;
using Microsoft.WindowsAzure.Storage.Blob;

namespace AzureEngine
{
    public class AzureEngine
    {
        //This file will contain the engine configurations for communicating with Azure
        private CloudStorageAccount storageAccount = null;

        public void InitStorage(String connectionString = null)
        {
            if (connectionString == null)
                connectionString = Environment.GetEnvironmentVariable("azureStorageConnectionString");

            if(CloudStorageAccount.TryParse(connectionString, out storageAccount))
            {
                Console.WriteLine("Successfully connected to storage account");
            }
            else
            {
                //Failure - alert user in a friendly manner
                Console.WriteLine("An error occurred in connecting to the storage account");
                Console.WriteLine("Please ensure the connection string is correct.");
                Console.WriteLine("Attempted to use connection string: " + connectionString);
            }
        }
    }
}
