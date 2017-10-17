from httplib2 import Http
import base64
import json
import time
import os
import signal
from urllib.parse import urlencode, quote_plus
from prometheus_client import start_http_server
from prometheus_client.core import GaugeMetricFamily, REGISTRY
import logging
from pythonjsonlogger import jsonlogger


class JenkinsApiClient():
    def __init__(self, config):
        self.config = config
        self.client = Http(cache=None, timeout=5)
        self.logger = logging.getLogger()

        # Generate auth digest
        if self.config["username"]:
            self.auth = base64.b64encode(bytearray(f"{self.config['username']}:{self.config['password']}", "UTF-8")).decode("UTF-8")
        else:
            self.auth = ""

    def request(self, path, params={}):
        # Encode query string
        query = urlencode(params, quote_via=quote_plus)
        url = self.config["url"] + path + "/api/json" + ("?" + query if query else "")

        # Prepare request headers
        headers = {}
        if self.auth:
            headers["Authorization"] = f"Basic {self.auth}"

        try:
            self.logger.debug(f"Fetching metrics from {url}")
            response, content = self.client.request(url, "GET", headers=headers)
        except Exception as error:
            self.logger.debug(f"Unable to fetch metrics from {url}", extra={"exception": str(error)})
            return {}

        # Check response code
        if response.status != 200:
            self.logger.debug(f"Unable to fetch metrics from {url} because response status code is {response.status}")
            return {}

        # Decode json
        try:
            data = json.loads(content)
        except Exception as error:
            self.logger.warning(f"Unable to decode metrics from {url}", extra={"exception": str(error)})
            return {}

        return {"data": data, "jenkins_version": response["x-jenkins"]}


class JenkinsMetricsCollector():
    def __init__(self, config):
        self.config = config
        self.client = JenkinsApiClient(config)

    def collect(self):
        metrics = self.get_jenkins_metrics()

        for name, metric in metrics.items():
            value = metric["value"]
            labels = metric["labels"] if "labels" in metric else {}

            gauge = GaugeMetricFamily(name, "", labels=labels.keys())
            gauge.add_metric(value=value, labels=labels.values())
            yield gauge

    def get_jenkins_metrics(self):
        metrics = {}
        metrics.update(self.get_jenkins_status_metrics())
        metrics.update(self.get_jenkins_queue_metrics())
        metrics.update(self.get_jenkins_plugins_metrics())

        # Add prefix to all metrics
        renamed = {}

        for key, value in metrics.items():
            renamed[self.config["metrics_prefix"] + "_" + key] = value

        return renamed

    def get_jenkins_status_metrics(self):
        # Fetch data from API
        response = self.client.request("/queue")

        if response:
            return {"up": {"value": 1, "labels": {"version": response["jenkins_version"]}}}
        else:
            return {"up": {"value": 0, "labels": {"version": ""}}}

    def get_jenkins_queue_metrics(self):
        # Fetch data from API
        response = self.client.request("/queue")
        if not response:
            return {}

        metrics = {"queue_oldest_job_since_seconds": {"value": 0}}

        # Get the oldest job in queue
        if len(response["data"]["items"]) > 0:
            oldest = min([item["inQueueSince"] for item in response["data"]["items"]], default=0)
            if oldest > 0:
                metrics["queue_oldest_job_since_seconds"]["value"] = time.time() - (oldest / 1000)

        return metrics

    def get_jenkins_plugins_metrics(self):
        # Fetch data from API
        response = self.client.request("/pluginManager", {"tree": "plugins[shortName,version,enabled,hasUpdate]"})
        if not response:
            return {}

        metrics = {
            "plugins_enabled_count":             {"value": 0},
            "plugins_enabled_with_update_count": {"value": 0}
        }

        # Count metrics
        for plugin in response["data"]["plugins"]:
            metrics["plugins_enabled_count"]["value"] += 1 if plugin["enabled"] else 0
            metrics["plugins_enabled_with_update_count"]["value"] += 1 if plugin["enabled"] and plugin["hasUpdate"] else 0

        return metrics


class SignalHandler():
    def __init__(self):
        self.shutdown = False

        # Register signal handler
        signal.signal(signal.SIGINT, self._on_signal_received)
        signal.signal(signal.SIGTERM, self._on_signal_received)

    def is_shutting_down(self):
        return self.shutdown

    def _on_signal_received(self, signal, frame):
        logging.getLogger().info("Exporter is shutting down")
        self.shutdown = True


if __name__ == '__main__':
    config = {
        "url":            os.environ.get("JENKINS_URL", ""),
        "username":       os.environ.get("JENKINS_USER", ""),
        "password":       os.environ.get("JENKINS_PASS", ""),
        "metrics_prefix": os.environ.get("METRICS_PREFIX", "jenkins"),
        "exporter_port":  int(os.environ.get("EXPORTER_PORT", "8000")),
        "log_level":      os.environ.get("EXPORTER_LOG_LEVEL", "INFO")
    }

    # Register signal handler
    signal_handler = SignalHandler()

    # Init logger
    logHandler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter("(asctime) (levelname) (message)", datefmt="%Y-%m-%d %H:%M:%S")
    logHandler.setFormatter(formatter)
    logging.getLogger().addHandler(logHandler)
    logging.getLogger().setLevel(config["log_level"])

    # Register our custom collector
    logging.getLogger().info("Exporter is starting up")
    REGISTRY.register(JenkinsMetricsCollector(config))

    # Start server
    start_http_server(config["exporter_port"])
    logging.getLogger().info(f"Exporter listening on port {config['exporter_port']}")

    while not signal_handler.is_shutting_down():
        time.sleep(1)

    logging.getLogger().info("Exporter has shutdown")
