# -*- coding: utf-8 -*-

import azure.storage.blob as azureblob
import os
import argparse

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-fp",
        "--filepath", 
        required=True,
        help="The path to the file on the node to process")
    parser.add_argument(
        "-bn",
        "--blobname",
        required=True,
        help="The full path the file should be saved to in the blob container")
    parser.add_argument(
        "-sa",
        "--storageaccount",
        required=True,
        help="The name of the Azure Storage account")
    parser.add_argument(
        "-sc",
        "--storagecontainer",
        required=True,
        help="The Azure Blob storage container name")
    parser.add_argument(
        "-st",
        "--sastoken",
        required=True,
        help="The SAS token providing write access to the Storage container.")

    args = parser.parse_args()

    # Create the blob client using the container"s SAS token.
    blob_client = azureblob.BlockBlobService(account_name=args.storageaccount, account_key=args.sastoken)

    print("Uploading file {0:} to container [{1:}]...".format(args.filepath, args.storagecontainer))

    blob_client.create_blob_from_path(args.storagecontainer, args.blobname, args.filepath)
