# Prometheus exporter for Jenkins


## How to run it

The exporter accepts configuration via environment variables. Ie.

`JENKINS_URL="https://my-jenkins.com" python exporter.py`

The following table shows the supported environment variables:

| Environment variable | Required | Default   | Description |
| -------------------- | -------- | --------- | ----------- |
| `JENKINS_URL`        | yes      |           | Jenkins endpoint |
| `JENKINS_USER`       | no       | `""`      | Login username |
| `JENKINS_PASS`       | no       | `""`      | Login password |
| `METRICS_PREFIX`     | no       | `jenkins` | Exported metrics prefix |
| `EXPORTER_PORT`      | no       | `8000`    | Exporter listening port |
| `EXPORTER_LOG_LEVEL` | no       | `INFO`    | Log level. Can ben `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |


## Exported metrics

This exporter has not been designed to export all Jenkins metrics, but code should be simply enough to fork and add metrics you need. The main reason is that we could export a bunch of metrics from Jenkins, but apparently everyone has a different use case. In our case, for example, we don't want to monitor Jenkins jobs status (since we believe it should be done by Jenkins itself), while we do export few metrics we care monitoring about.

```
jenkins_up
jenkins_queue_oldest_job_since_seconds
jenkins_plugins_enabled_count
jenkins_plugins_enabled_with_update_count
```


## Contributions

### Ensure the code is PEP 8 compliant

`pycodestyle --max-line-length=180 prometheus-jenkins-exporter/__init__.py`


## License

This software is released under the [MIT license](LICENSE.txt).
