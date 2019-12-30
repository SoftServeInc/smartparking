FROM ubuntu:16.04

RUN apt-get update
RUN apt-get install -y python3 python3-pip libsm6 libxext6 libxrender-dev
RUN rm -rf /var/lib/apt/lists/*
RUN apt-get update
RUN apt-get install -y libglib2.0-0

RUN pip3 install -U pip
COPY requirements.txt /tmp/
RUN pip3 install -r /tmp/requirements.txt

WORKDIR /opt/model/

COPY crop_helpers.py /opt/model/
COPY model_core.py /opt/model/
COPY model_helpers.py /opt/model/
COPY model_wrapper.py /opt/model/
COPY weather_augmentations.py /opt/model/

ENV MODELS_PATH /opt/model/trained_models/
ENV MODEL_CONFIG /opt/model/model_configurations/model_config.json
ENV SOURCE_IMG_FOLDER /opt/model/pklot_images/
ENV CAMERA_IMG_CONFIG_FOLDER /opt/model/pklot_configurations/

ENTRYPOINT ["python3", "model_wrapper.py"]
