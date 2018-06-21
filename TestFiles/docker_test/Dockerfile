FROM python:2
WORKDIR /usr/src/app

# Install python azure storage package to enable sending result to the BLOB
RUN pip install azure-storage==0.32.0

# Copy the python application to the docker container
COPY app.py ./

# Run the python application
CMD ["python2" "./app.py"]