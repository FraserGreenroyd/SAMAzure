#FROM python:2
#WORKDIR /usr/src/app

# Install python azure storage package to enable sending result to the BLOB
#RUN pip install azure-storage==0.32.0

# Copy the python application to the docker container
#COPY app.py ./

# Run the python application
#CMD ["python2" "./app.py"]



# Base image
FROM ubuntu:14.04

# About
MAINTAINER Tristan Gerrish "Tristan.Gerrish@BuroHappold.com"

# Install EnergyPlus
ENV ENERGYPLUS_VERSION 8.8.0
ENV ENERGYPLUS_TAG v8.8.0
ENV ENERGYPLUS_SHA 7c3bbe4830

# This should be x.y.z, but EnergyPlus convention is x-y-z
ENV ENERGYPLUS_INSTALL_VERSION 8-8-0

# Downloading from Github
# e.g. https://github.com/NREL/EnergyPlus/releases/download/v8.8.0/EnergyPlus-8.8.0-7c3bbe4830-Linux-x86_64.sh
ENV ENERGYPLUS_DOWNLOAD_BASE_URL https://github.com/NREL/EnergyPlus/releases/download/$ENERGYPLUS_TAG
ENV ENERGYPLUS_DOWNLOAD_FILENAME EnergyPlus-$ENERGYPLUS_VERSION-$ENERGYPLUS_SHA-Linux-x86_64.sh
ENV ENERGYPLUS_DOWNLOAD_URL $ENERGYPLUS_DOWNLOAD_BASE_URL/$ENERGYPLUS_DOWNLOAD_FILENAME

# Collapse the update of packages, download and installation into one command to make the container smaller & remove a bunch of the auxiliary apps/files that are not needed in the container
RUN apt-get update && apt-get install -y ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -SLO $ENERGYPLUS_DOWNLOAD_URL \
    && chmod +x $ENERGYPLUS_DOWNLOAD_FILENAME \
    && echo "y\r" | ./$ENERGYPLUS_DOWNLOAD_FILENAME \
    && rm $ENERGYPLUS_DOWNLOAD_FILENAME \
    && cd /usr/local/EnergyPlus-$ENERGYPLUS_INSTALL_VERSION \
    && rm -rf DataSets Documentation ExampleFiles WeatherData MacroDataSets PostProcess/convertESOMTRpgm \
    PostProcess/EP-Compare PreProcess/FMUParser PreProcess/ParametricPreProcessor PreProcess/IDFVersionUpdater

# Remove the broken symlinks
RUN cd /usr/local/bin \
    && find -L . -type l -delete

# INSTALL RADIANCE
RUN cd /tmp \
    && wget https://github.com/NREL/Radiance/releases/download/5.1.0/radiance-5.1.0-Linux.tar.gz \
    && tar -xzvf radiance-5.1.0-Linux.tar.gz \
    && cp -a radiance-5.1.0-Linux/usr/local/radiance/bin/. /usr/local/bin \
    && cp -a radiance-5.1.0-Linux/usr/local/radiance/lib/. /usr/local/lib/ray

# INSTALL PYTHON
RUN apt-get install python2.7
RUN apt install python-pip


WORKDIR /usr/local/lib/python2.7/site-packages

# copy ladybug
COPY ./ladybug ./ladybug
# copy honeybee
COPY ./honeybee ./honeybee


# Install Radiance


# Install Energyplus






