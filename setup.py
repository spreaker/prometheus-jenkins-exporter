from setuptools import setup

setup(
  name = 'prometheus-jenkins-exporter',
  packages = ['prometheus_jenkins_exporter'],
  version = '0.2.4',
  description = 'Prometheus exporter for Jenkins',
  author = 'Marco Pracucci',
  author_email = 'marco@pracucci.com',
  url = 'https://github.com/spreaker/prometheus-jenkins-exporter',
  download_url = 'https://github.com/spreaker/prometheus-jenkins-exporter/archive/0.2.2.tar.gz',
  keywords = ['prometheus', 'jenkins'],
  classifiers = [],
  python_requires = '>=3',
  install_requires=['httplib2==0.10.3', 'prometheus_client==0.0.21', 'python-json-logger==0.1.5'],
  entry_points={
    'console_scripts': [
        'jenkins-exporter=prometheus_jenkins_exporter.exporter:main',
    ]
  }
)
