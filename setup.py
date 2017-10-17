from distutils.core import setup
setup(
  name = 'prometheus-jenkins-exporter',
  packages = ['prometheus-jenkins-exporter'],
  version = '0.1.2',
  description = 'Prometheus exporter for Jenkins',
  author = 'Marco Pracucci',
  author_email = 'marco@pracucci.com',
  url = 'https://github.com/spreaker/prometheus-jenkins-exporter',
  download_url = 'https://github.com/spreaker/prometheus-jenkins-exporter/archive/0.1.2.tar.gz',
  keywords = ['prometheus', 'jenkins'],
  classifiers = [],
  python_requires = '>=3',
  entry_points={
    'console_scripts': [
        'jenkins-exporter=prometheus-jenkins-exporter.exporter:main',
    ]
  }
)