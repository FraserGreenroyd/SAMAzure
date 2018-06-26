# -*- coding: utf-8 -*-
"""
Created on Sun Oct  8 09:56:17 2017

@author: Antoine
"""

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
    parser.add_argument('--blobname', required=True,
                        help='The full path the file should be saved to on the'
                              'blob storage')
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
    # parser.add_argument('--blob_path', required=True,
    #                     help='The path on the blob where the file is saved.')
    args = parser.parse_args()

    # Create the blob client using the container's SAS token.
    # This allows us to create a client that provides write
    # access only to the container.
    blob_client = azureblob.BlockBlobService(account_name=args.storageaccount,
                                                 sas_token=args.sastoken)

    # output_file_path = os.path.realpath(args.filepath)
    # filepath = args.filepath

    print('Uploading file {} to container [{}]...'.format(args.blobname.rsplit("/",1)[1],
            args.storagecontainer))

    blob_client.create_blob_from_path(args.storagecontainer,
                                      args.blobname,
                                      args.filepath)
