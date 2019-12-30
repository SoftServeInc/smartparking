FROM alpine:3.8

RUN apk add --no-cache ffmpeg

WORKDIR /data

EXPOSE 554 8090

ENTRYPOINT ["/entrypoint.sh"]
