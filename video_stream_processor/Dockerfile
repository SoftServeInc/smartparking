FROM jrottenberg/ffmpeg:3.3

WORKDIR /opt/workdir

RUN apt-get update
RUN apt-get install -y python

ENV IMAGES_OUTPUT_DIR /opt/workdir/output_images/

COPY ffmpeg_launcher.py /opt/workdir/

ENTRYPOINT ["python", "ffmpeg_launcher.py", "config.json"]
