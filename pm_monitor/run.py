from .metrics import MetricMaker
from .sensor_database import SensorDatabase
from .server import create_app
#from .rtl433 import rtl433
from .pm_monitor import PMDcommunicator, find_ch340_comport
from .outdoor_humidity import get_message2, get_humidity
import threading
import time
import os

def run(metric_descriptions=None, metric_filters=None):
    if metric_descriptions is None:
        metric_descriptions = []
    if metric_filters is None:
        metric_filters = []
    
    db = SensorDatabase()

    metric_maker = MetricMaker(metric_descriptions, metric_filters)

    #receiver = rtl433()
    receiver = PMDcommunicator(find_ch340_comport())
    receiver.setSendTime("000")
    receiver.setStoreTime("000")
    
    error_event = threading.Event()
    def rx_thread_entry():
        count = 0
        while True:
            try:
                count += 1
                if count > 86400/5: # for ~24 hours 86400/5, for ~1 hour 86400/(5*24)
                    count = 0
                    print("setting clock")
                    print("clock return:", receiver.setClock())
                message, error, error2 = receiver.get_message() # Accounts for 0.5 sleep seconds
                receiver.pushStopPMdetector() # Accounts for 1 sleep second
                print("message 100=", message)
                print("error2=", error2)
                time.sleep(3.5)
                if message is not None:
                    db.store(message)
                else:
                    print("error =", error)
                    print("error2 =", error2)
            except:
                print("exception raised while trying to get a new messages")
                error_event.set()
                raise
        
    rx_thread = threading.Thread(target=rx_thread_entry, daemon=False)
    rx_thread.start()

    def rx2_thread_entry():
        while True:
            try:
                message = get_message2()
                print("message 110=", message)
                time.sleep(30)
                if message is not None:
                    db.store(message)
            except:
                print("exception raised while trying to get a new messages")
                error_event.set()
                raise
        
    rx2_thread = threading.Thread(target=rx2_thread_entry, daemon=False)
    rx2_thread.start()

    host = os.getenv('PM_MONITOR_HOST', "0.0.0.0")
    port = os.getenv('PM_MONITOR_PORT', "5000")
    def http_thread_entry():
        try:
            app = create_app(db,  metric_maker)
            app.run(host=host, port=port)
        except:
            error_event.set()
            print("error event, http")
            raise
    
    http_thread = threading.Thread(target=http_thread_entry, daemon=True)
    http_thread.start()

    while(not error_event.wait()):
        print("no error event")
        pass
    if error_event.wait():
        print("there must be an error event raised")

    time.sleep(1)