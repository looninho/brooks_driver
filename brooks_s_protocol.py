# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:        brooks_s_protocol.py
# Purpose:     driver for communicating with MFC SLA58XX series
#
# Notes:       This code has been adapted from PyExpLabSys
# Authors of original Code:   Robert Jensen, Kenneth Nielsen
# Modified by Luan Nguyen (2020)
# Copyright:   (c) David Naylor
# Licence:     GPL-3.0
# Website:     https://github.com/CINF/PyExpLabSys/blob/master/PyExpLabSys/drivers/brooks_s_protocol.py
#-------------------------------------------------------------------------------
import time
import struct
import logging
import serial
from six import b, indexbytes

class Brooks(object):
    """ Driver for Brooks s-protocol """
    def __init__(self, device, port='/dev/ttyUSB0'):
        self.ser = serial.Serial(port, 19200)
        self.ser.parity = serial.PARITY_ODD
        self.ser.bytesize = serial.EIGHTBITS
        self.ser.stopbits = serial.STOPBITS_ONE
        deviceid = self.comm('8280000000000b06'
                             + self.pack(device[-8:]))
        manufactor_code = deviceid[6:8]
        device_type = deviceid[8:10]
        long_address = manufactor_code + device_type + deviceid[-6:]
        self.long_address = long_address

    def pack(self, input_string):
        """ Turns a string in packed-ascii format """
        #This function lacks basic error checking....
        klaf = ''
        for s in input_string:
            klaf += bin((ord(s) % 128) % 64)[2:].zfill(6)
        result = ''
        for i in range(0, 6):
            result = result + hex(int('' + klaf[i * 8:i * 8 + 8],
                                      2))[2:].zfill(2)
        return result

    def crc(self, command):
        """ Calculate crc value of command """
        i = 0
        while command[i:i + 2] == 'FF':
            i += 2
        command = command[i:]
        n = len(command)
        result = 0
        for i in range(0, (n//2)):
            byte_string = command[i*2:i*2+2]
            byte = int(byte_string, 16)
            result = byte ^ result
        return hex(result)

    def comm(self, command):
        """ Implements low-level details of the s-protocol 
        return 2 bytes status code and data."""
        check = str(self.crc(command))
        check = check[2:].zfill(2)
        final_com = 'FFFFFFFF' + command + check
        bin_comm = ''
        for i in range(0, len(final_com) // 2):
            bin_comm += chr(int(final_com[i * 2:i * 2 + 2], 16))
        bin_comm += chr(0)
        bytes_for_serial = b(bin_comm)
        error = 1
        while (error > 0) and (error < 10):
            self.ser.write(bytes_for_serial)
            time.sleep(0.2)
            s = self.ser.read(self.ser.inWaiting())
            st = ''
            for i in range(0, len(s)):
                #char = hex(ord(s[i]))[2:].zfill(2)
                #char = hex(s[i])[2:].zfill(2)
                char = hex(indexbytes(s, i))[2:].zfill(2)
                if not char.upper() == 'FF':
                    st = st + char
            try:
                # delimiter = st[0:2]
                # address = st[2:12]
                command = st[12:14]
                byte_count = int(st[14:16], 16)
                response = st[16:16 + 2 * byte_count]
                error = 0
            except ValueError:
                error = error + 1
                response = 'Error'
        return response[:4], response[4:]

    @staticmethod
    def get_bytes(n, data, nb=1):
        return data[2*n:2*n+2*nb]

    @staticmethod
    def ieee_pack(value):
        ieee = struct.pack('>f', value)
        ieee_value = ''
        for i in range(4):
            ieee_value += hex(ieee[i])[2:].zfill(2)
        return ieee_value

    @staticmethod
    def ieee_unpack(ieee_str):
        ieee = bytes.fromhex(ieee_str)
        return struct.unpack('>f', ieee)

    def __comm(self, cmd):
        return self.comm('82' + self.long_address + cmd)

    def read_flow(self): #command #1
        """ Read the current flow-rate """
        status, data = self.__comm('0100') # command = 01 byte count = 00
        try:  # TODO: This should be handled be re-sending command
            unit_code = int(Brooks.get_bytes(0,data,1),16)
            value = Brooks.ieee_unpack(Brooks.get_bytes(1,data,4))value
        except ValueError:
            value = -1
            unit_code = 171  # Satisfy assertion check, we know what is wrong
        #assert unit_code == 171  # Flow unit should always be mL/min
        return value

    def read_full_range(self): #command #151 for SLA-series
        """
        Report the full range of the device
        Apparantly command #152 does not work for SLA-series...
        """
        status, data = self.__comm('970101') #Command 151
        try:  # TODO: This should be handled be re-sending command
            gas_selection_code = int(Brooks.get_bytes(0,data,1),16)
            density_unit_code = int(Brooks.get_bytes(1,data,1),16)
            process_gas_density = Brooks.ieee_unpack(Brooks.get_bytes(2,data,4))[0]
            reference_temperature_unit_code = int(Brooks.get_bytes(6,data,1),16)
            reference_temperature_value = Brooks.ieee_unpack(Brooks.get_bytes(7,data,4))[0]
            reference_pressure_unit_code = int(Brooks.get_bytes(11,data,1),16)
            reference_pressure_value = Brooks.ieee_unpack(Brooks.get_bytes(12,data,4))[0]
            unit_code = int(Brooks.get_bytes(16,data,1),16) #reference_flow_unit_code
            value = Brooks.ieee_unpack(Brooks.get_bytes(17,data,4))[0] #reference_flow_range_value
        except ValueError:
            value = -1
            unit_code = 171  # Satisfy assertion check, we know what is wrong
        #assert unit_code == 171  # Flow unit should always be mL/min
        return value

    def set_flow(self, flowrate): #command #236
        """ Set the setpoint of the flow """
        ieee_flowrate = Brooks.ieee_pack(flowrate)
        #ec05: ec = cmd 236; 05 = len(unit_code + ieee_sp)
        #39 (57 dec) = unit code for percent; FA (250 dec)= unit code for 'same unit as flowrate measurement'
        status, data = self.__comm('ec05' + 'FA' + ieee_flowrate)
        percent_unit = int(Brooks.get_bytes(0,data,1),16) #always 57 (39 hex)
        setpoint_percent = Brooks.ieee_unpack(Brooks.get_bytes(1,data,4))[0]
        select_unit = int(Brooks.get_bytes(5,data,1),16) # 250 (FA), etc.
        setpoint = Brooks.ieee_unpack(Brooks.get_bytes(6,data,4))[0]
        return setpoint

    def select_flow_unit(self, flow_unit, flow_ref=0): #command #196
        byte0 = hex(flow_ref)[2:].zfill(2)
        byte1 = hex(flow_unit)[2:].zfill(2)
        status, data = self.__comm('c402' + byte0 + byte1)
        flag = byte0 == data[:2] and byte1 == data[2:]
        return flag

    #TODO def totalizers: commands 240-242

if __name__ == "__main__":

    print('\nBrooks MFC SLA58XX series driver\n')
    
    tag='28478010'
    
    # setup the rs485 comm port:
    BROOKS = Brooks(tag,'COM2') #CRHEA=COM5, HOME=COM8
    
    # command 11:
    response=BROOKS.comm('8280000000000b06'+BROOKS.pack(tag))
    print(response)
    
    # long address:
    print(BROOKS.long_address)
    
    # read flow:
    print(BROOKS.read_flow())
