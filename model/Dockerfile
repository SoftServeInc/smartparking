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

COPY model_core.py /opt/model/
COPY model_wrapper.py /opt/model/

ENV MODEL_PATH /opt/model/trained_models/
ENV MODEL_CONFIG /opt/model/model_configurations/model_config.json
ENV INFERENCE_CONFIG /opt/model/inference_configurations/inference_config.yaml
ENV CAMERA_IMG_CONFIG_FOLDER /opt/model/pklot_configurations/
ENV SOURCE_IMG_FOLDER /opt/model/pklot_images/

ENTRYPOINT ["python3", "model_wrapper.py"]
