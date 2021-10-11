#!/bin/bash

# BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}/.." )" >/dev/null 2>&1 && pwd )"
IMAGE="update_meeting_calendar"

docker run -it --rm \
    -e GOOGLE_APPLICATION_CREDENTIALS="/workspace/etc/service_account.json" \
    -v "$(pwd):/workspace" \
    -v "$(pwd)/../../etc:/workspace/etc" \
    -w /workspace \
    "${IMAGE}"
