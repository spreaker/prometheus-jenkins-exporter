FROM alpine:3.11

# Installing required packages
RUN apk add --upgrade --no-cache \
    python3

WORKDIR /workspace/prometheus-jenkins-exporter

# Install dependencies
COPY requirements.txt ./requirements.txt
RUN pip3 install -r requirements.txt
