#!/bin/sh
nohup ffserver &
ffmpeg -re -f lavfi -i "movie=filename=sample.mp4:loop=0, setpts=N/(FRAME_RATE*TB)" http://localhost:8090/feed.ffm
