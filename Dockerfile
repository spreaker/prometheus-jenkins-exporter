FROM alpine:3.8

# Installing required packages
RUN apk add --update --no-cache \
    python3

# Install dependencies
COPY requirements.txt /workspace/prometheus-jenkins-exporter/requirements.txt
RUN cd /workspace/prometheus-jenkins-exporter && pip3 install -r requirements.txt

WORKDIR /workspace/prometheus-jenkins-exporter
