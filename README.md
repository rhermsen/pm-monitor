# Credit
This repo is forked from the [monitor_rtl433](https://github.com/mcbridejc/monitor_rtl433) and adapted to my needs.

# PM-monitor

A wrapper to collect data from 'PM Detector' PM2.5, temperature and humidity sensors using serial over USB, and make it available as metrics in [prometheus format](https://github.com/prometheus/docs/blob/master/content/docs/instrumenting/exposition_formats.md). 

## Requirements

The PM-Detector connected via a local USB port. 

## Setup

This program is just a simple python wrapper that initializes the PM-Detector and collects its output, while running a webserver to serve out the collected data.

After installing the package, you can run it simply with `python -m pm_monitor`, and then visit `localhost:5000`.
Out-of-the box, the `/sensors` route will show raw data from any detected sensors, but the `/metrics` route will be blank. 

Setting up the `/metrics` routes requires a little more work to define which sensors you want to generate metrics from, and how they should be defined. See [examples/main.py](examples/main.py) for an example of how to create `MetricDescription` and `MetricFilter` objects and provide these to `pm_montor.run()`.

![Sensors Table](/images/example_sensors_table.png?raw=true "Sensors Table")