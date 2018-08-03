import azure.storage.blob as azureblob
import os
import argparse

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--filepath', required=True,
                        help='The path to the text file to process. The path'
                             'may include a compute node\'s environment'
                             'variables, such as'
                             '$AZ_BATCH_NODE_SHARED_DIR/filename.txt')
    parser.add_argument('--filename', required=True,
                        help='The name of the folder where daylight calcs'
                              'have been performed')
    parser.add_argument('--storageaccount', required=True,
                        help='The name the Azure Storage account that owns the'
                             'blob storage container to which to upload'
                             'results.')
    parser.add_argument('--storagecontainer', required=True,
                        help='The Azure Blob storage container to which to'
                             'upload results.')
    parser.add_argument('--sastoken', required=True,
                        help='The SAS token providing write access to the'
                             'Storage container.')
    args = parser.parse_args()

    # Create the blob client using the container's SAS token.
    # This allows us to create a client that provides write
    # access only to the container.
    blob_client = azureblob.BlockBlobService(account_name=args.storageaccount,
                                                 sas_token=args.sastoken)

    output_file_path = os.path.realpath(args.filepath)
    filename = args.filename

    print('Uploading file {} to container [{}]...'.format(output_file_path,
            args.storagecontainer))

    blob_client.create_blob_from_path(args.storagecontainer,
                                      filename,
                                      output_file_path)