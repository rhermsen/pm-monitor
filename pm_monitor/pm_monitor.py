# -*- coding: utf-8 -*-
"""
Created on Sun Apr  2 00:19:34 2023
Version 0.1 2023-04-02 01:16
Version 0.4 2023-04-03 21:52
Version 0.5 2023-04-03 23:08:
    added exception handling in method readPMdetector after a JSONDecodeError.
Version 0.6 2023-04-03 17:50:
    Added timeout mechanims in methods which read 'JSON format' from the serial buffer.
Version 0.7 2023-04-24 16:40:
    added exception handling in method readPMdetector after a UnicodeDecodeError
Version 0.9 2023-05-06 02:21:
    For method readPMdetector returning an error message in case of returning None.
    Requeres a change in run.py also.
Version 1.0 2023-05-09 21:12:
    Moving to 1.0 (i.s.o. 0.9x).
    Extending method get_message to return the data as part of the error message.
Version 1.1 2023-05-11 00:06:
    Return messages when setting clock.
Version 1.2 2023-05-12 16:46:
    Extend the pushStartPMdetector(), readPMdetector() and get_message() method's to return status and cascaded error information.
Version 1.3 2023-05-13 18:02:
    Adding more temporarly debug information for the setClock() method.
Version 1.4 2023-05-14 01:02:
    Commented out the temporarly debug information for the setClock() method.
    Included a 1 second sleep after the pushStopPMdetector() to prevent subsequent commands to become flushed.
Version 1.51 2023-05-21 02:54:
    Added out_waiting in_buffer content size to error_message
    # prepare for future update:
        # Extend the pushStopPMdetector() method to also flush the output buffer, and for both flush commands use the new 3.0 commands.
        # Use a 0.5 second delay between the two commands, and another 0.5 seconds delay after the last flush command.
    Cleanup of some unused code.
Version 1.52 2023-05-23 18:03:
    Corrected version 1.51
Version 1.6 2023-05-24 14:01:
    Added an time.sleep(0.5) after each write where it expects data in return from the PM-detector.
Version 1.7 2023-06-09 23:55:
    Add getters and setters (clear) for read and write buffers, because with in_ and out_ I'm keep mixing them up.
Version 1.8 2023-06-10 12:34:
    Determined that 20ms sleep is the minimum needed to wait for the whole JSON string to arrive in the read buffer.
    Will use a 0.4s sleep in the pushStopPMdetector() reset the write_buffer sleep another 0.4s reset the read_buffer
    and use a 0.2s sleep at the end, so pushStopPMdetector() will still in total contribute to a 1s sleep.
    Also reset the read_buffer in case wrong response-type was receieved in method get_message() and pushStartPMdetector().
Version 1.9 2023-06-22 19:30:
    The write_buffer gets send (emptied) in just a few milliseconds. No additional measures are needed.
    Still see a problem with Grafana getting into 'No data' state.
    Get a timeout for both pushStartPMdetector(), readPMdetector(). Added buffer data information to the error messages for both.
Version 2.0 2023-06-22 22:59:
    Return 'None' if PM2.5 reading is > 800
Version 2.1 2023-06-25 23:45:
    Include the actual reading if PM2.5 reading is above 800 in error message

	
	
@author: rhermsen

ToDo:
    - All methods that have a loop reading JSON formatted data from the serial buffer should have a timeout mechanism.
    - All methods that send data to the PM-Monitor should have a 0.5 to 1 second delay to wait for data to return.
        - this will introduce extra delay of 1 to 2 seconds per data read cycle. 
        - 6 locations where data is written. The pushStopPMdetector() method doesn't need an additonal delay.
    - There are 5 other places where a UnicodeDecodeError can occur, create exception handling for these places.
    - Change return on exception to include more failure info, e.g.     return None, serial_decode
    - Following examples introduces a 0.5 to 1 second delay after sending a string, before reading a response:
        https://stackoverflow.com/questions/676172/full-examples-of-using-pyserial-package
        Maybe I can change this to 'try for upto 1 second to read the first character from serial'...
    - Verify if read_until can be used to read char's till '}'
    
"""

#
# https://github.com/pyserial/pyserial
# pip install pyserial
# https://pyserial.readthedocs.io/en/latest/pyserial.html
import serial
import serial.tools.list_ports
import json
import time
from datetime import datetime


class PMDcommunicator(object):
    def __init__(self, comPort):
        '''
        Parameters
        ----------
        comPort : string, e.g. "COM4" the com port used by the USB to Serial CH340 driver.
        
            DESCRIPTION:
                Class to communicate with the PM Detector. After instantiation the following is possible.
                Initialize the sendtime and/or storetime (function 01 for sendtime, and function 02 for storetime).
                Retrieve the current configured parameters (function 80).
                Trigger the PM Detector to start pushing data via the serial port every sendtime seconds (function 05).
                Request the PM Detector to stop pushing data via the serial port (function 05).
                Have the PM Detector dump all historical data. (function 04) The amount of historical data present can be retrieved via function 80.
                Delete all historical data stored in the PM Detector. (function 06)
                close the serial connection with the com port.
                Set the date and time of the PM Detector

                (usb.transfer_type == 0x03) && (usb.endpoint_address == 0x02) && (usb.src == "host")
                usb.addr == "1.9.2"
                
            Ref:
                https://github.com/msillano/tuyaDAEMON/wiki/custom-device-'PM-detector':-case-study
                https://frdmtoplay.com/patching-in-fahrenheit/

        Returns
        -------
        None.
        '''
        self.comPort = comPort
        self.baudrate = 115200
        self.bytesize = 8
        self.timeout = 2
        self.stopbits = serial.STOPBITS_ONE
        self.serialPort = serial.Serial(port=self.comPort, baudrate=self.baudrate, bytesize=self.bytesize, timeout=self.timeout, stopbits=self.stopbits)
        self.SendInteralTime = None
        self.StoreInteralTime = None
        self.WritePoint = None
        self.ReadPoint = None
        self.SendInteralFlag = None
        self.writepointerror = None
        self.readpointerror = None
        self.getParameterTime = None
    

    def closePort(self):
        self.serialPort.close()
   
    
    def setSendTime(self, sendTime, timeout=30):
        '''
        Parameters
        ----------
        sendTime : string, a 3 digit string between "000" and "999", with "000" one measurement output only.
        
            DESCRIPTION:
                Setter for the sendTime, the period in seconds the PM Detecter will use to push out data.
            
        Returns
        -------
        None.
        '''
        if int(sendTime) > 999 or len(sendTime) != 3:
            print('Only string lengths of 3 are supported with a value between "000" to "999".')
            exit(1)
        sendTimeString = '{"fun":"01","sendtime":"' + sendTime.zfill(3) + '"}\n' #Obtain data every pushData seconds.
        self.serialPort.write(sendTimeString.encode('Ascii'))
        time.sleep(0.5)
        PMData = ' '
        startTime = time.time()
        while PMData[-1] != '}':
            # https://stackoverflow.com/questions/606191/convert-bytes-to-a-string
            try:
                PMData += self.serialPort.read(1).decode("Ascii")
            except:
                return None
            timeNow = time.time()
            if timeNow - startTime > timeout:
                return None
        # https://www.geeksforgeeks.org/python-convert-string-dictionary-to-dictionary/
        if int(json.loads(sendTimeString)['fun']) == int(json.loads(PMData)['res']):
            pass
        self.getPMdetectorParameters()
    

    def setStoreTime(self, storeTime, timeout=30):
        '''
        Parameters
        ----------
        storeTime : string, a 3 digit string between "000" and "999".
        
            DESCRIPTION:
                Setter for the storeTime, the period in seconds the PM Detector will use to store data internally.
                
            ToDo:
                - Handle "JSONDecodeError: Extra data" in line:
                    if int(json.loads(initString)['fun']) == int(json.loads(PMData)['res']):
                - If storeTime is other than 3 digit string e.g. "001" it causes odd values.
                  "1" > "000037", "2" > "000137", "3" > "000237", "4" > "000337", "5" > "000437", "6" > "000537", "7" > "000637", "8" > "000737", "9" > "000837"
                  "00" > "065522" > "FFF2" > ~18hours, "01" > "065532" > "FFFC" > ~18hours,
                  "02" > "000006", "03" > "000016", "04" > "000026", "05" > "000036", "04" > "000046", "07" > "000056", "08" > "000066", "09" > "000076"
                  "10" > "000086", "11" > "000096"
                  "9999" > "000999", "09999" > "000099"
        Returns
        -------
        None.
        '''
        if int(storeTime) > 999 or len(storeTime) != 3:
            print('Only string lengths of 3 are supported with a value between "000" to "999".')
            exit(1)
        storeTimeString = '{"fun":"02","storetime":"' + storeTime.zfill(3) + '"}\n' #
        self.serialPort.write(storeTimeString.encode('Ascii'))
        time.sleep(0.5)
        PMData = ' '
        startTime = time.time()
        while PMData[-1] != '}':
            # https://stackoverflow.com/questions/606191/convert-bytes-to-a-string
            try:
                PMData += self.serialPort.read(1).decode("Ascii")
            except:
                return None
            timeNow = time.time()
            if timeNow - startTime > timeout:
                return None
        # https://www.geeksforgeeks.org/python-convert-string-dictionary-to-dictionary/
        if int(json.loads(storeTimeString)['fun']) == int(json.loads(PMData)['res']):
            pass
        self.getPMdetectorParameters()
    

    def pushStartPMdetector(self, timeout=30):
        '''
        Description:
            Send string to PM Detector to start sending data via serial port.
            This will be confirmed by the PM Detector by sending {"res":"5"} as response.
    
        Returns
        -------
        bool, True if the push data sequence was successful confirmed by the PM Detector.
        '''
        try:
            initStartString = '{"fun":"05","flag":"1"}\n' #Start obtaining data with last submitted sendtime.
            self.serialPort.write(initStartString.encode('Ascii'))
            time.sleep(0.5)
        except Exception as e:
            error_message = "Serial write: ErrorType : {}, Error : {}".format(type(e).__name__, e)
            return False, error_message
        PMData = ' '
        startTime = time.time()
        while PMData[-1] != '}':
            # https://stackoverflow.com/questions/606191/convert-bytes-to-a-string
            try:
                PMData += self.serialPort.read(1).decode("Ascii")
            except Exception as e:
                error_message = "Serial read: ErrorType : {}, Error : {}".format(type(e).__name__, e)
                return False, error_message
            timeNow = time.time()
            if timeNow - startTime > timeout:
                error_message = "Serial read: timeout" + " read buffer:" + str(self.getReadBuffer()) + " write buffer:" + str(self.getWriteBuffer())
                return False, error_message
        # https://www.geeksforgeeks.org/python-convert-string-dictionary-to-dictionary/
        try:
            if int(json.loads(initStartString)['fun']) == int(json.loads(PMData)['res']):
                self.SendInteralFlag = True
                error_message = ''
                return True, error_message
            else:
                error_message = "Failed to start sending data via serial port"
                return False, error_message
        except Exception as e:
            error_message = "JSON decode PMData: ErrorType : {}, Error : {}".format(type(e).__name__, e)
            error_message = error_message + str(PMData) + str(len(PMData))
            try:
                error_message = error_message + " read buffer:" + str(self.getReadBuffer())
            except:
                pass
            if len(PMData) >= 20:
                # Received response much larger than expected. Correct response is probably still in serial buffer.
                time.sleep(0.5)
                self.clearReadBuffer()
                time.sleep(0.5)
            return False, error_message
        

    def pushStopPMdetector(self):
        '''
        Description:
            Send string to PM Detector to stop sending data via serial port.
            Note: There is no confirmation this was successful, serial output will just stop.
            It will also flush any remaining characters from the input buffer.
            There is a one second sleep to prevent any subsequent send command to become flushed.

            NOTE: Take the 1 second sleep into account in the calling script.

            Ref:
                https://stackoverflow.com/questions/60766714/pyserial-flush-vs-reset-input-buffer-reset-output-buffer
        
        Returns
        -------
        None.
        '''
        initStopString = '{"fun":"05","flag":"0"}\n' #Start obtaining data with last submitted sendtime.
        self.serialPort.write(initStopString.encode('Ascii'))
        self.SendInteralFlag = False
        time.sleep(0.4)
        self.clearWriteBuffer()
        time.sleep(0.4)
        self.clearReadBuffer()
        time.sleep(0.2)


    def readPMdetector(self, timeout=30):
        '''
        Description:
            Reads one dataset via serial output from the connected PM Detector.
            
        Ref:
            https://stackoverflow.com/questions/13180941/how-to-kill-a-while-loop-with-a-keystroke
            Not tried: https://stackoverflow.com/questions/510357/how-to-read-a-single-character-from-the-user
            https://stackoverflow.com/questions/26838953/python-read-from-serial-port-and-encode-as-json
            https://stackoverflow.com/questions/606191/convert-bytes-to-a-string
            https://thispointer.com/how-to-append-text-or-lines-to-a-file-in-python/
            
        ToDo:
            -
        Done:
            - If sendTime = "000" only one data-string is expected. In case of missing the closing character this function will wait forever.
            Find a solution e.g. a timeout, to prevent waiting forever.
            
        Returns
        -------
        None.
        '''
        retry = 0
        if self.SendInteralFlag == None or self.SendInteralFlag == False:
            retry += 1
            result, error_message2 = self.pushStartPMdetector()

        # https://stackoverflow.com/questions/26838953/python-read-from-serial-port-and-encode-as-json
        PMData = ' '
        startTime = time.time()
        while PMData[-1] != '}':
            # https://stackoverflow.com/questions/606191/convert-bytes-to-a-string
            #PMData.append(serialPort.read(1).decode("utf-8"))
            #PMData += serialPort.read(1).decode("utf-8")
            try:
                PMData += self.serialPort.read(1).decode("Ascii")
            except Exception as e:
                error_message = "ErrorType : {}, Error : {}".format(type(e).__name__, e)
                return None, error_message, error_message2
            timeNow = time.time()
            if timeNow - startTime > timeout:
                error_message = "timeout" + " read buffer:" + str(self.getReadBuffer()) + " write buffer:" + str(self.getWriteBuffer())
                return None, error_message, error_message2
        try:
            jsonExport = json.loads(PMData)
            return jsonExport, None, error_message2
        except Exception as e:
            error_message = "ErrorType : {}, Error : {}".format(type(e).__name__, e)
            return None, error_message, error_message2


    def getPMdetectorParameters(self, timeout = 30):
        '''
        Description:
            Retrieve the parameter details from the PM Detector, and return these details as JSON data (dictionary).
            Also stores the separate values in variables.
            
            ToDo:
                - 
            Done:
                - handle "UnicodeDecodeError: 'ascii' codec can't decode byte 0xf5 in position 0: ordinal not in range(128)".
                  0xf5 = UTF8 "LATIN SMALL LETTER O WITH TILDE"
                  "WritePoint":"\xf567295","ReadPoint":"\xf567295"
                  https://charbase.com/00f5-unicode-latin-small-letter-o-with-tilde
                  This is now solved, but no clue how the PM Monitor got into this state.
                  The 'WritePoint' got normalized after a getPMDdata.deletePMdetectorData().
                  The 'ReadPoint' is now 'y15455'.
                - Largest "WritePoint" value = "WritePoint":"172800" next value = "WritePoint":"000000"
                  
        Returns
        -------
        jsonExport : Dictionary, JSON format dictionary with the current parameters.
        '''
        if self.SendInteralFlag == True:
            self.pushStopPMdetector()
        dumpString = '{"fun":"80"}\n'
        self.serialPort.write(dumpString.encode('Ascii'))
        time.sleep(0.5)
        PMData = ' '
        empty_buffer = 0
        startTime = time.time()
        while PMData[-1] != '}' and  empty_buffer <= 10:
            if self.getReadBuffer() == 0:
                empty_buffer += 1
            # https://stackoverflow.com/questions/606191/convert-bytes-to-a-string
            #PMData += self.serialPort.read(1).decode("Ascii")
            #PMData += self.serialPort.read(1).decode("utf-8")
            char = self.serialPort.read(1)
            if char != b'\xf5':
                try:
                    PMData += char.decode("Ascii")
                except:
                    return None
            timeNow = time.time()
            if timeNow - startTime > timeout:
                error_message = "timeout"
                return error_message
        if len(PMData) > 2 and PMData[-2] == ',':
            PMData = PMData[:-2] + PMData[-1]
            jsonExport = json.loads(PMData)
        else:
            return None
        if int(json.loads(PMData)['res']) == 80:
            #self.getParameterTime = str(datetime.now()).split(".")[0]
            #self.getParameterTime = (datetime.strptime(self.iterationTime, '%Y-%m-%d %H:%M:%S'))
            self.getParameterTime = datetime.now()
            if int(json.loads(PMData)['SendInteralFlag']) == 1:
                self.SendInteralFlag = True
            elif int(json.loads(PMData)['SendInteralFlag']) == 0:
                self.SendInteralFlag = False
            self.SendInteralTime = int(json.loads(PMData)['SendInteralTime'])
            self.StoreInteralTime = int(json.loads(PMData)['StoreInteralTime'])
            self.WritePoint = json.loads(PMData)['WritePoint']
            self.ReadPoint = json.loads(PMData)['ReadPoint']
            return jsonExport
    
        
    def getSendTime(self):
        '''
        DESCRIPTION:
            Getter for the sendTime parameter.

        Returns
        -------
        int, the integer value of sendTime.
        '''
        if self.SendInteralTime == None:
            self.getPMdetectorParameters()
        return self.SendInteralTime
    

    def getStoreTime(self):
        '''
        DESCRIPTION:
            Getter for the storeTime parameter.

        Returns
        -------
        int, the integer value of storeTime.
        '''
        if self.StoreInteralTime == None:
            self.getPMdetectorParameters()
        return self.StoreInteralTime
    

    def getWritePoint(self):
        '''
        DESCRIPTION:
            Getter for the WritePoint parameter.

        Returns
        -------
        string, the string value of the WritePoint. 
        '''
        if self.WritePoint == None:
            self.getPMdetectorParameters()
        try:
            if (datetime.now() - self.getParameterTime).total_seconds() >= 30:
                self.getPMdetectorParameters()
        except TypeError:
            self.getPMdetectorParameters()
        return self.WritePoint
    

    def getReadPoint(self):
        '''
        DESCRIPTION:
            Getter for the ReadPoint parameter.

        Returns
        -------
        string, the string value of the ReadPoint.
        '''
        if self.ReadPoint == None:
            self.getPMdetectorParameters()
        return self.ReadPoint
    

    def getSendFlag(self):
        '''
        DESCRIPTION:
            Getter if SendFlag is set or not.

        Returns
        -------
        bool, True if SendFlag is 1, False if SendFlag is 0.
        '''
        if self.SendInteralFlag == None:
            self.getPMdetectorParameters()
        return self.SendInteralFlag
    

    def getWriteBuffer(self):
        """
        DESCRIPTION:
            Getter for the current write buffer content to be sent to serial port.

        Returns
        -------
        int, Amount of characters in the output buffer.       
        """
        return self.serialPort.out_waiting


    def getReadBuffer(self):
        """
        DESCRIPTION:
            Getter for the current read buffer content coming from the serial port.

        Returns
        -------
        int, Amount of characters in the input buffer.       
        """
        return self.serialPort.in_waiting


    def clearWriteBuffer(self):
        """
        DESCRIPTION:
            Clear (setter) the write buffer of content to be sent via serial port.
        """
        self.serialPort.reset_output_buffer()


    def clearReadBuffer(self):
        """
        DESCRIPTION:
            Clear (setter) the read buffer of content received via serial port.
        """
        self.serialPort.reset_input_buffer()    


    def setClock(self, timeout=30):
        '''
        DESCRIPTION:
            Setter of the clock to the current time of the pc.
            
            The clock is set in the format: (YY-MM-DD hh:mm:ss)
            
            Ref:
                https://stackoverflow.com/questions/606191/convert-bytes-to-a-string
                https://www.geeksforgeeks.org/python-convert-string-dictionary-to-dictionary/

        Returns
        -------
        None.
        '''
        # {"fun":"03","clock":"21-03-05 20:57:24"}}  {"res":"3"}                     (YY-MM-DD hh:mm:ss)
        currentClock = datetime.now()
        setClockString = '{"fun":"03","clock":"' + currentClock.strftime("%y-%m-%d %H:%M:%S")  + '"}\n'
        try:
            #print("Trying to set clock using string:", setClockString)
            self.serialPort.write(setClockString.encode('Ascii'))
            time.sleep(0.5)
        except Exception as e:
            error_message = "ErrorType : {}, Error : {}".format(type(e).__name__, e)
            return error_message
        PMData = ' '
        startTime = time.time()
        while PMData[-1] != '}':
            # https://stackoverflow.com/questions/606191/convert-bytes-to-a-string
            try:
                PMData += self.serialPort.read(1).decode("Ascii")
            except Exception as e:
                error_message = "ErrorType : {}, Error : {}".format(type(e).__name__, e)
                return error_message
            timeNow = time.time()
            if timeNow - startTime > timeout:
                error_message = "timeout"
                return error_message
            #print('PMData =', PMData)
        # https://www.geeksforgeeks.org/python-convert-string-dictionary-to-dictionary/
        if int(json.loads(setClockString)['fun']) == int(json.loads(PMData)['res']):
            message = "successfull setting clock"
            return message
        else:
            message = "unsuccessfull setting clock without error"
            return message
        
    
    def get_message(self, timeout=30):
        """Read data from the serial buffer.
        
        Returns
        -------
        Message as a dict, or None if no message is obtained from the buffer.
        """
        data_dict, error_message, error_message2 = self.readPMdetector(timeout)
        message_dict = {}

        if (isinstance(data_dict, dict)) and (len(data_dict) == 16):
            #construct timestamp
            message_dict["time"] = data_dict["y"] + \
                                '-' + data_dict["m"] + \
                                '-' + data_dict["d"] + \
                                ' ' + data_dict["h"] + \
                                ':' + data_dict["min"] + \
                                ':' + data_dict["sec"]
            message_dict["model"] = "PM-Monitor"
            message_dict["id"] = 100
            message_dict["temperature_C"] = data_dict["t"]
            message_dict["humidity"] = data_dict["r"]
            message_dict["pm2_5"] = data_dict["cpm2.5"]
            message_dict["pm1_0"] = data_dict["cpm1.0"]
            message_dict["pm10"] = data_dict["cpm10"]
            if int(data_dict["cpm2.5"]) > 800:
                return None, f'PM2.5 reading above 800, reading {data_dict["cpm2.5"]}', ''
            else:
            return message_dict, '', ''
        else:
            if error_message == None:
                error_message = "Lenght data_dict = " + str(len(data_dict)) + " data_dict = " + str(data_dict)
                try:
                    error_message = error_message + " read buffer:" + str(self.getReadBuffer())
                except:
                    pass 
                try:
                    if len(data_dict) == 1 and data_dict["res"] == "5":
                        # Received the wrong response type. Correct response is probably still in serial buffer. 
                        time.sleep(0.5)
                        self.clearReadBuffer()
                        time.sleep(0.5)
                except Exception as e:
                    pass
            return None, error_message, error_message2


def find_ch340_comport():
    """
    Find the comport of the PM Monitor. This function assumes there is only one ch340 device present.
    Ref:
        https://stackoverflow.com/questions/34889768/finding-a-specific-serial-com-port-in-pyserial-windows
        https://stackoverflow.com/questions/49341960/typeerror-from-use-of-in-re-searchrerere-string
    
    Returns
    -------
    Comport number as a string, string.
    """
    try:
        ch340portList = list(serial.tools.list_ports.grep("CH340|USB Serial"))
        if len(ch340portList) == 1:
            return ch340portList[0][0]
        elif len(ch340portList) == 0:
            print("PM Monitor is not connected. Please connect PM Monitor to a USB port with a data cable.")
            exit(1)
        else:
            print("Mutliple USB-Serial CH340 devices connected. Cannot determine the correct device.")
    except StopIteration:
        print("PM Monitor is not connected. Please connect PM Monitor to a USB port with a data cable.")
        exit(1)
