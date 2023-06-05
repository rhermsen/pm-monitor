from pm_monitor import run
from pm_monitor.metrics import Metric, MetricFilter, MetricDescription

def degc2f(x):
    return x * 9.0/5.0 + 32.0

class PmMonitor(MetricFilter):
    def __init__(self, id):
        self.id = id
        # The `_match` property will be used to determine which sensor records
        # this filter will be applied to
        self._match = {"model": "PM-Monitor", "id" : self.id}
        
    def process(self, r):
        """Takes a single sensor record, and converts it to 0 or more metrics
        """
        sensor_id = "PM-Monitor_%s" % (str(self.id)) 
        yield Metric('temperature', r['temperature_C'], labels={'sensor_id': sensor_id})
        yield Metric('humidity', r['humidity'], labels={'sensor_id': sensor_id})
        yield Metric('pm2_5', r['pm2_5'], labels={'sensor_id': sensor_id})
        yield Metric('pm1_0', r['pm1_0'], labels={'sensor_id': sensor_id})
        yield Metric('pm10', r['pm10'], labels={'sensor_id': sensor_id})

class OutdoorHumidity(MetricFilter):
    def __init__(self, id):
        self.id = id
        # The `_match` property will be used to determine which sensor records
        # this filter will be applied to
        self._match = {"model": "Outdoor Humidity", "id" : self.id}
        
    def process(self, r):
        """Takes a single sensor record, and converts it to 0 or more metrics
        """
        sensor_id = "OutdoorHumidity_%s" % (str(self.id)) 
        yield Metric('humidity', r['humidity'], labels={'sensor_id': sensor_id})

class AcuriteTower(MetricFilter):
    def __init__(self, id):
        self.id = id
        # The `_match` property will be used to determine which sensor records
        # this filter will be applied to
        self._match = {"model": "Acurite tower sensor", "id" : self.id}
        
    def process(self, r):
        """Takes a single sensor record, and converts it to 0 or more metrics
        """
        sensor_id = "%s%s" % (str(self.id), r['channel']) 
        yield Metric('temperature', degc2f(r['temperature_C']), labels={'sensor_id': sensor_id})
        yield Metric('humidity', r['humidity'], labels={'sensor_id': sensor_id})
        yield Metric('battery_warning', r['battery_low'], labels={'sensor_id': sensor_id})

class LaCrosse(MetricFilter):
    def __init__(self, id):
        self.id = id
        self._match = {"model": "TX141TH-Bv2 sensor", "id": self.id}

    def process(self, r):
        sensor_id = "LaCross_%s" % (str(self.id))
        battery_warning = 0
        if r['battery'] == "OK":
            battery_warning = 0
        elif r['battery'] == "LOW":
            battery_warning = 1
        else:
            battery_warning = 99 # Unrecognized. (I'm not sure right now what all the battery field options are)

        yield Metric('temperature', degc2f(r['temperature_C']), labels={'sensor_id': sensor_id})
        yield Metric('humidity', r['humidity'], labels={'sensor_id': sensor_id})
        yield Metric('battery_warning', battery_warning, labels={'sensor_id': sensor_id})

def main():
    # List all metric names that we will expose
    metric_descriptions = [
        MetricDescription("temperature", "gauge", "Temperature in degrees C"),
        MetricDescription("humidity", "gauge", "Relative humidity in percent"),
        MetricDescription("pm2_5", "gauge", "particulate matter of size 2.5 um in μg/m3"),
        MetricDescription("pm1_0", "gauge", "particulate matter of size 1 um in μg/m3"),
        MetricDescription("pm10", "gauge", "particulate matter of size 10 um in μg/m3"),
    ]
    # For each sensor that we want to convert to metrics, create a MetricFilter class that will do that
    metric_filters = [
        PmMonitor(100),
        OutdoorHumidity(110)
    ]

    run(metric_descriptions, metric_filters)

if __name__ == '__main__':
    main()