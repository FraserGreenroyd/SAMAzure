using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

using Microsoft.WindowsAzure.Storage;
using Microsoft.WindowsAzure.Storage.Blob;

using Microsoft.Azure.Batch;

using System.IO;

namespace AzureEngine.AzureObjects
{
    public class BlobStorage
    {
        private CloudStorageAccount storageAccount = null;
        private CloudBlobContainer blobContainer = null;
        private SystemMessageContainer messageContainer = null;

        public BlobStorage(String connectionString = null, SystemMessageContainer container = null)
        {
            if (connectionString == null) throw new NullReferenceException("Please provide a connection string for creating blob storage on Azure");

            messageContainer = (container == null ? new SystemMessageContainer() : container);

            if (CloudStorageAccount.TryParse(connectionString, out storageAccount))
                messageContainer.AddInformationMessage("Successfully connected to storage account");
            else //Failure - alert user in a friendly manner
                messageContainer.AddErrorMessage("An error occurred in connecting to the storage account", "Attempted to use connection string: " + connectionString);
        }

        public async Task SendFile(String filePath, String fileName)
        {
            if (storageAccount == null) return;

            try
            {
                messageContainer.AddInformationMessage("Creating Blob Client...");
                CloudBlobClient blobClient = storageAccount.CreateCloudBlobClient();

                messageContainer.AddInformationMessage("Creating Blob Container...");
                blobContainer = blobClient.GetContainerReference("enginetestblob" + Guid.NewGuid().ToString());
                await blobContainer.CreateAsync();
                messageContainer.AddInformationMessage("Blob Container " + blobContainer.Name + " created");

                messageContainer.AddInformationMessage("Setting Blob Permissions...");
                BlobContainerPermissions blobPermissions = new BlobContainerPermissions { PublicAccess = BlobContainerPublicAccessType.Blob };
                await blobContainer.SetPermissionsAsync(blobPermissions);

                String fullFile = filePath + fileName;

                messageContainer.AddInformationMessage("Uploading file...");
                CloudBlockBlob blobBlock = blobContainer.GetBlockBlobReference(fileName);
                await blobBlock.UploadFromFileAsync(fullFile);
                messageContainer.AddInformationMessage("File uploaded...");
            }
            catch (Exception e)
            {
                messageContainer.AddErrorMessage("An error occurred. Details are below", e.ToString());
            }
        }

        public async Task DownloadFile(String filePath, String fileName, String downloadFile)
        {
            String fullFile = filePath + fileName;

            try
            {
                CloudBlockBlob blobBlock = blobContainer.GetBlockBlobReference(downloadFile);

                messageContainer.AddInformationMessage("Downloading blob file to " + fullFile);
                await blobBlock.DownloadToFileAsync(fullFile, System.IO.FileMode.Create);
                messageContainer.AddInformationMessage("File downloaded...");
            }
            catch (Exception e)
            {
                messageContainer.AddErrorMessage("An error occurred. Details are below", e.ToString());
            }
        }

        public async Task DeleteBlob()
        {
            if (blobContainer == null) return;

            messageContainer.AddInformationMessage("Deleting the blob container...");
            await blobContainer.DeleteIfExistsAsync();
            messageContainer.AddInformationMessage("Blob container deleted");
        }

        public ResourceFile GenerateResourceFile(String fileName = null)
        {
            if (fileName == null) return null;

            SharedAccessBlobPolicy sasConstraints = new SharedAccessBlobPolicy
            {
                SharedAccessExpiryTime = DateTime.UtcNow.AddHours(2),
                Permissions = SharedAccessBlobPermissions.Read
            };

            CloudBlockBlob blobBlock = blobContainer.GetBlockBlobReference(fileName);
            String sasBlobToken = blobBlock.GetSharedAccessSignature(sasConstraints);
            String blobSasUri = String.Format("{0}{1}", blobBlock.Uri, sasBlobToken);

            return new ResourceFile(blobSasUri, Path.GetFileName(fileName));
        }
    }
}
