# sound-level-meter

App designed to record and alert on sound levels at grass-roots motorsports events.

Designed for use with a digitech QM1592, but may work with QM1598 (not yet tested)

## Application Architecture

- slm-log.py provides the application

- influxDB provides a data store

- Grafana provides graphing

- Pushover provides application alerts

## Features

- Logging to database
- Logging to CSV for noise violation detection
- Logging to a separate CSV for compliance reasons (e.g. club rules might require 250ms samples for detection, but local compliance might only require 1 second samples)
- Dashboard for threshold analysis
- Alerting on:
    - Application Start
    - Noise violation

## Hardware
- Raspberry Pi 5 with Raspbian with python3
    - 8GB version
    - NVMe case with NVMe drive
- Digitech QM1592 

## Installation
These instructions assume that influxDB and Grafana have already been installed.

### Python
Runs in a python virtual environment.  
- Create a application directory
- Copy src/app/slm-log.py and src/app/slm-log.ini
- Create the virual environment
- Install prerequisites

```
mkdir sound-level-meter
cd sound-level-meter
cp {gitrepo}/src/app/slm-log.py .
cp {gitrepo}/src/app/slm-log.ini .
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
```

- Create the influxdb bucket ```sound-level-meter```
- Create an API Token (Load Data/API Tokens in the InfluxDB console) with access to the sound-level-meter bucket
- Edit the ```slm-log.ini``` file and update values as necessary
- run the code ```python3 slm-log.py```

## Acknowlegements
This project used SilkyClouds NoiseBuster for inspiration.

https://github.com/silkyclouds/NoiseBuster/tree/main
