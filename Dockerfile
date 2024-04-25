#!/usr/bin/python

# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License

FROM python:3.11-alpine
SHELL ["/bin/sh", "-c"]

# Create a directory to hold the persistent data
WORKDIR /app

# Copy the requirements file
COPY requirements.txt requirements.txt

# Install dependencies
RUN python3 -m pip install --no-cache-dir -r requirements.txt

RUN apt install graphviz

# Define volumes to persist output
VOLUME ["/app/target"]

# Copy the files and folders to the persistent directory
COPY . .

ENTRYPOINT ["/bin/sh"]