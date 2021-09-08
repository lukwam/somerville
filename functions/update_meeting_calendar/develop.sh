#!/bin/bash

IMAGE="update_meeting_calendar"

docker run -it --rm \
    -w /usr/src \
    -v "$(pwd):/usr/src" \
    "${IMAGE}" python main.py

