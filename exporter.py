from httplib2 import Http
import base64
import json
import time
import os
from urllib.parse import urlencode, quote_plus
from prometheus_client import start_http_server
from prometheus_client.core import GaugeMetricFamily, REGISTRY
import logging
from pythonjsonlogger import jsonlogger


# TODO handle SIGTERM


class JenkinsApiClient():
    def __init__(self, config):
        self.config = config
        self.client = Http(cache=None, timeout=5)
        self.logger = logging.getLogger()

        # Generate auth digest
        if self.config["username"] != "":
            self.auth = base64.b64encode(bytearray("{:s}:{:s}".format(self.config["username"], self.config["password"]), "UTF-8")).decode("UTF-8")
        else:
            self.auth = ""

    def request(self, path, params = {}):
        # Encode query string
        query   = urlencode(params, quote_via=quote_plus)
        url     = self.config["url"] + path + "/api/json" + ("?" + query if query != "" else "")

        # Prepare request headers
        headers = {}
        if self.auth != "":
            headers["Authorization"] = "Basic {:s}".format(self.auth)

        try:
            self.logger.debug("Fetching metrics from {:s}".format(url))
            response, content = self.client.request(url, "GET", headers=headers)
        except Exception as error:
            self.logger.debug("Unable to fetch metrics from {:s}".format(url), extra={ "exception": str(error) })
            return False

        # Check response code
        if response.status != 200:
            self.logger.debug("Unable to fetch metrics from {:s} because response status code is {:d}".format(url, response.status))
            return False

        # Decode json
        try:
            data = json.loads(content)
        except Exception as error:
            self.logger.warning("Unable to decode metrics from {:s}".format(url), extra={ "exception": str(error) })
            return False

        return { "data": data, "jenkins_version": response["x-jenkins"] }




class JenkinsMetricsCollector():
    def __init__(self, config):
        self.config = config
        self.client = JenkinsApiClient(config)

    def collect(self):
        metrics = self.get_jenkins_metrics()

        for name, metric in metrics.items():
            value  = metric["value"]
            labels = metric["labels"] if "labels" in metric else {}

            gauge = GaugeMetricFamily(name, "", labels=labels.keys())
            gauge.add_metric(value=value,labels=labels.values())
            yield gauge

    def get_jenkins_metrics(self):
        metrics = {}
        metrics.update(self.get_jenkins_status_metrics())
        metrics.update(self.get_jenkins_queue_metrics())
        metrics.update(self.get_jenkins_plugins_metrics())

        # Add prefix to all metrics
        renamed = {}

        for key, value in metrics.items():
            renamed[self.config["metrics_prefix"] + "_" + key] = value

        return renamed

    def get_jenkins_status_metrics(self):
        # Fetch data from API
        response = self.client.request("/queue")

        if response != False:
            return { "up": { "value": 1, "labels": { "version": response["jenkins_version"]} } }
        else:
            return { "up": { "value": 0, "labels": { "version": "" } } }

    def get_jenkins_queue_metrics(self):
        # Fetch data from API
        response = self.client.request("/queue")
        if response == False:
            return {}

        metrics = { "queue_oldest_job_since_seconds": { "value": 0 } }

        # Get the oldest job in queue
        if len(response["data"]["items"]) > 0:
            oldest = min([item["inQueueSince"] for item in response["data"]["items"]], default = 0)
            if oldest > 0:
                metrics["queue_oldest_job_since_seconds"]["value"] = time.time() - (oldest / 1000);

        return metrics

    def get_jenkins_plugins_metrics(self):
        # Fetch data from API
        response = self.client.request("/pluginManager", { "tree": "plugins[shortName,version,enabled,hasUpdate]" })
        if response == False:
            return {}

        metrics = {
            "plugins_enabled_count":             { "value": 0 },
            "plugins_enabled_with_update_count": { "value": 0 }
        }

        # Count metrics
        for plugin in response["data"]["plugins"]:
            metrics["plugins_enabled_count"]["value"]             += 1 if plugin["enabled"] else 0
            metrics["plugins_enabled_with_update_count"]["value"] += 1 if plugin["enabled"] and plugin["hasUpdate"] else 0

        return metrics




if __name__ == '__main__':
    config = {
        "url":            os.environ["JENKINS_URL"],
        "username":       os.environ["JENKINS_USER"] if "JENKINS_USER" in os.environ else "",
        "password":       os.environ["JENKINS_PASS"] if "JENKINS_PASS" in os.environ else "",
        "metrics_prefix": os.environ["METRICS_PREFIX"] if "METRICS_PREFIX" in os.environ else "jenkins",
        "exporter_port":  os.environ["EXPORTER_PORT"] if "EXPORTER_PORT" in os.environ else 8000
    }

    # Init logger
    logHandler = logging.StreamHandler()
    formatter  = jsonlogger.JsonFormatter()
    logHandler.setFormatter(formatter)
    logging.getLogger().addHandler(logHandler)
    # TODO add timestamp and level to logger output
    # TODO configurabile da fuori
    logging.getLogger().setLevel(logging.DEBUG)

    # Register our custom collector
    logging.getLogger().info("Exporter is starting up")
    REGISTRY.register(JenkinsMetricsCollector(config))

    # Start server
    start_http_server(config["exporter_port"])
    logging.getLogger().info("Exporter listening on port {:d}".format(config["exporter_port"]))

    while True:
        time.sleep(60)
