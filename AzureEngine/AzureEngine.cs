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
        private CloudBlobContainer blobContainer = null;

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

        public async Task SendFile(String filePath, String fileName)
        {
            if (storageAccount == null) return;

            try
            {
                Console.WriteLine("Creating Blob Client...");
                CloudBlobClient blobClient = storageAccount.CreateCloudBlobClient();

                Console.WriteLine("Creating Blob Container...");
                blobContainer = blobClient.GetContainerReference("enginetestblob" + Guid.NewGuid().ToString());
                await blobContainer.CreateAsync();
                Console.WriteLine("Blob Container " + blobContainer.Name + " created");
                Console.WriteLine();

                Console.WriteLine("Setting Blob Permissions...");
                BlobContainerPermissions blobPermissions = new BlobContainerPermissions { PublicAccess = BlobContainerPublicAccessType.Blob };
                await blobContainer.SetPermissionsAsync(blobPermissions);

                String fullFile = filePath + fileName;

                Console.WriteLine("Uploading file... Started at " + DateTime.Now);
                CloudBlockBlob blobBlock = blobContainer.GetBlockBlobReference(fileName);
                await blobBlock.UploadFromFileAsync(fullFile);
                Console.WriteLine("File uploaded. Finished at " + DateTime.Now);
            }
            catch (Exception e)
            {
                Console.WriteLine("An error occurred. Details are below");
                Console.WriteLine(e.ToString());
            }
        }

        public async Task DownloadFile(String filePath, String fileName, String downloadFile)
        {
            String fullFile = filePath + fileName;

            try
            {
                CloudBlockBlob blobBlock = blobContainer.GetBlockBlobReference(downloadFile);

                Console.WriteLine("Downloading blob file to " + fullFile + ". Started at " + DateTime.Now);
                await blobBlock.DownloadToFileAsync(fullFile, System.IO.FileMode.Create);
                Console.WriteLine("File downloaded. Finished at " + DateTime.Now);
            }
            catch (Exception e)
            {
                Console.WriteLine("An error occurred. Details are below");
                Console.WriteLine(e.ToString());
            }
        }

        public async Task DeleteBlob()
        {
            if (blobContainer == null) return;

            Console.WriteLine("Deleting the blob container...");
            await blobContainer.DeleteIfExistsAsync();
            Console.WriteLine("Blob container deleted");
        }
    }
}
