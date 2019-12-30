FROM python:3.7-rc-alpine

RUN pip install paho-mqtt
RUN apk --no-cache add musl-dev linux-headers g++
RUN pip install numpy

WORKDIR /opt/workdir/flow

ENV PYTHONPATH /opt/workdir/flow/

COPY events.py /opt/workdir/flow/core_engine/
COPY rules.py /opt/workdir/flow/core_engine/
COPY parking_state.py /opt/workdir/flow/core_engine/
COPY core_engine_launcher.py /opt/workdir/flow/core_engine/
COPY __init__.py /opt/workdir/flow/core_engine/
COPY windowing.py /opt/workdir/flow/core_engine/

ENTRYPOINT ["python", "core_engine/core_engine_launcher.py", "config.json", "reservation.json"]
