# Prometheus exporter for Jenkins


## How to install

The following will install the exporter whose entrypoint binary is called `jenkins-exporter`:

```
pip3 install prometheus-jenkins-exporter
```


## How to run it

The exporter accepts configuration via environment variables. Ie.

`JENKINS_URL="https://my-jenkins.com" jenkins-exporter`

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
jenkins_slave_up
```


## Contributions

### Run the development environment

```
docker-compose build && docker-compose run dev sh
```

### Ensure the code is PEP 8 compliant

`pycodestyle --max-line-length=180 prometheus_jenkins_exporter/*.py`


### How to publish a new version

1. [Release new version on GitHub](https://github.com/spreaker/prometheus-jenkins-exporter/releases)
2. Update version in `setup.py`
3. Run `python3 setup.py sdist upload -r pypi`


## License

This software is released under the [MIT license](LICENSE.txt).
