import azure.storage.blob as azureblob
import os
import argparse

def add_the_inputs(x, y):
    return x + y

with open("result.txt", "w") as f:
    f.write(str(add_the_inputs(21, 21)))

blob_client = azureblob.BlockBlobService(account_name="radfiles", sas_token="?sv=2017-11-09&ss=bfqt&srt=sco&sp=rwdlacup&se=2018-06-21T19:43:27Z&st=2018-06-21T11:43:27Z&spr=https&sig=zJmAQNMzkw8RN2voMT2ZiPTM9P%2F7gQqBJH2S9U0F2ng%3D")
blob_client.create_blob_from_path("testing", "result.txt", "result.txt")