from httplib2 import Http
import base64
import json
import time
import os
import signal
import faulthandler
from threading import Lock
from urllib.parse import urlencode, quote_plus
from prometheus_client import start_http_server
from prometheus_client.core import GaugeMetricFamily, REGISTRY
import logging
from pythonjsonlogger import jsonlogger


# Enable dumps on stderr in case of segfault
faulthandler.enable()


class JenkinsApiClient():
    def __init__(self, config):
        self.config = config
        self.client = Http(cache=None, timeout=5)
        self.clientLock = Lock()
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

            # Wrap the HTTP client access with an exclusive lock
            # because the library is not thread safe
            if not self.clientLock.acquire(timeout=30):
                raise Exception("Unable to get lock on HTTP client")

            try:
                response, content = self.client.request(url, "GET", headers=headers)
            finally:
                self.clientLock.release()
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

        for metric in metrics:
            name = metric["name"]
            value = metric["value"]
            labels = metric["labels"] if "labels" in metric else {}

            gauge = GaugeMetricFamily(name, "", labels=labels.keys())
            gauge.add_metric(value=value, labels=labels.values())
            yield gauge

    def get_jenkins_metrics(self):
        metrics = []
        metrics.extend(self.get_jenkins_status_metrics())
        metrics.extend(self.get_jenkins_queue_metrics())
        metrics.extend(self.get_jenkins_plugins_metrics())

        for slave in self._get_slaves():
            metrics.extend(self.get_jenkins_slave_metrics(slave))

        # Add prefix to all metrics
        renamed = []

        for metric in metrics:
            metric["name"] = self.config["metrics_prefix"] + "_" + metric["name"]
            renamed.append(metric)

        return renamed

    def get_jenkins_status_metrics(self):
        # Fetch data from API
        response = self.client.request("/queue")

        if response:
            return [{"name": "up", "value": 1, "labels": {"version": response["jenkins_version"]}}]
        else:
            return [{"name": "up", "value": 0, "labels": {"version": ""}}]

    def _get_slaves(self):
        # Fetch data from API
        response = self.client.request("/computer")

        if not response:
            return []

        # Get all slaves
        slaves = []
        for slave in response["data"]["computer"]:
            if slave["_class"] == "hudson.slaves.SlaveComputer":
                slaves.append(slave)

        return slaves

    def get_jenkins_slave_metrics(self, slave):
        # Get slave status
        status = 0
        if slave["offline"] or slave["temporarilyOffline"]:
            status = 0
        else:
            status = 1

        metrics = [
            {
                "name": "slave_up",
                "value": status,
                "labels": {"display_name": slave['displayName']}
            }
        ]

        return metrics

    def get_jenkins_queue_metrics(self):
        # Fetch data from API
        response = self.client.request("/queue")
        if not response:
            return []

        metrics = [
            {"name": "queue_oldest_job_since_seconds", "value": 0}
        ]

        # Get the oldest job in queue
        if len(response["data"]["items"]) > 0:
            oldest = min([item["inQueueSince"] for item in response["data"]["items"]], default=0)
            if oldest > 0:
                metrics[0]["value"] = time.time() - (oldest / 1000)

        return metrics

    def get_jenkins_plugins_metrics(self):
        # Fetch data from API
        response = self.client.request("/pluginManager", {"tree": "plugins[shortName,version,enabled,hasUpdate]"})
        if not response:
            return []

        plugins_enabled_count = 0
        plugins_enabled_with_update_count = 0

        # Count metrics
        for plugin in response["data"]["plugins"]:
            plugins_enabled_count += 1 if plugin["enabled"] else 0
            plugins_enabled_with_update_count += 1 if plugin["enabled"] and plugin["hasUpdate"] else 0

        return [
            {
                "name": "plugins_enabled_count",
                "value": plugins_enabled_count,
            },
            {
                "name": "plugins_enabled_with_update_count",
                "value": plugins_enabled_with_update_count,
            }
        ]


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


def main():
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


if __name__ == '__main__':
    main()
