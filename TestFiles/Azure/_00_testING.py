# Copy the file back to the blob
import azure.storage.blob as azureblob
import os
import argparse

# Write a file containing something awesome!
with open("test_output.txt", "w") as f:
    f.write("If you're reading this ... it worked!!! Also, Hello World!")

parser = argparse.ArgumentParser()
parser.add_argument(
    '--filepath',
    required=True,
    help='The path to the text file to process. The path may include a compute node\'s environment variables, such as $AZ_BATCH_NODE_SHARED_DIR/filename.txt'
)

parser.add_argument(
    '--blobname',
    required=True,
    help='The full path the file should be saved to on theblob storage'
)

parser.add_argument(
    '--storageaccount',
    required=True,
    help='The name the Azure Storage account that owns the blob storage container to which to upload results.'
)

parser.add_argument(
    '--storagecontainer',
    required=True,
    help='The Azure Blob storage container to which to upload results.'
)

parser.add_argument(
    '--sastoken',
    required=True,
    help='The SAS token providing write access to the Storage container.'
)

args = parser.parse_args()

# Create the blob client using the container's SAS token. This allows us to create a client that provides write access only to the container.
blob_client = azureblob.BlockBlobService(
    account_name=args.storageaccount,
    sas_token=args.sastoken
)

print(
    'Uploading file {} to container [{}]...'.format(
        args.blobname.rsplit("/", 1)[1],
        args.storagecontainer
    )
)

blob_client.create_blob_from_path(
    args.storagecontainer,
    args.blobname,
    args.filepath
)