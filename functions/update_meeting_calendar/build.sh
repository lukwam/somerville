#!/bin/bash

IMAGE="update_meeting_calendar"

pack build "${IMAGE}" --builder gcr.io/buildpacks/builder:v1
