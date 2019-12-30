FROM python:3.7-rc-alpine

RUN pip install paho-mqtt

WORKDIR /opt/workdir/flow

ENV IMAGES_INPUT_DIR /opt/workdir/input_images/
ENV ARCHIVE_DIR /opt/workdir/archive_images/
ENV PYTHONPATH /opt/workdir/flow/

COPY history_manager.py /opt/workdir/flow/history_manager/

ENTRYPOINT ["python", "history_manager/history_manager.py", "config.json"]
