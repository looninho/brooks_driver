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

class ErrorStatus(Exception):
    """ Example:
    ```python
    raise ErrorStatus('blabla...')
    ```
    """
    pass

class Brooks(object):
    """ Driver for Brooks s-protocol series SLA58XX.

    See *X-DPT-RS485-SLA5800-SLAMf-Series-RevB-MFC-PC-RT-eng.pdf* document 
    for implementing the below class methods. In the rest of this help, 
    *SLA document* will be referenced to this document.

    Args:
        tag: 8-digits tag number
        port: comport
    """
    def __init__(self, tag, uartdriver):
        #self.ser = serial.Serial(port, 19200)
        #self.ser.parity = serial.PARITY_ODD
        #self.ser.bytesize = serial.EIGHTBITS
        #self.ser.stopbits = serial.STOPBITS_ONE
        self.ser = uartdriver
        deviceid = self.comm('8280000000000b06'
                             + self.pack(tag[-8:]))
        manufactor_code = deviceid[6:8]
        device_type = deviceid[8:10]
        long_address = manufactor_code + device_type + deviceid[-6:]
        self.long_address = long_address

    def pack(self, input_string):
        """ Turns a string in packed-ascii format.
        
        c.f. *SLA document* page (21), section 3-4-8-5 Packed-ASCII (6-bit ASCII) Data Format
        
        Args:
            input_string: the ascii text to pack. It is the tag alphanumerical
            8-characters string, i.e. `12345678`

        Returns:
            The packed (6_bits) ASCII text.
        """
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
        """ Calculate crc value of command.

        c.f. *SLA document* page (22), section 3-4-8-6 Checksum Characters
        
        Args:
            command: the command to be calculated.
            
        Returns:
            the calculated crc.
        """
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
        if len(ieee_str) < 8:
            ieee_str += '0'*(8-len(ieee_str))
        ieee = bytes.fromhex(ieee_str)
        return struct.unpack('>f', ieee)

    def comm(self, command):
        """ Implements low-level details of the s-protocol.

        Args:
            command: the command to send.

        Returns:
            2 bytes status code and data.
        """
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
        return response

    def comm2(self, cmd):
        """ Same as `comm()` but splitted to: status, data.

        Args:
            command: the command to send without delimiter character and long address.

        Returns:
            `status`, `data`.
        """
        response = self.comm('82' + self.long_address + cmd)
        return response[:4], response[4:]

    def read_flow(self): #command #1
        """ c.f. *SLA document* page (36), section 6-2 Command #1 Read
        Primary Variable.
        
        Read the primary variable. The primary variable is the flow
        rate or pressure of the device expressed in the selected flow
        units at the selected flow reference conditions. See Command #196
        for information on setting Flow Units, and Flow Reference
        conditions.

        *N.B.* Assignment of flow or pressure to the Primary Variable is
        dependent on the type of Brooks SLA Series device. See Section 1-1.

        Returns:
            `primary variable` (float).
         """

        status, data = self.comm2('0100') # command = 01 byte count = 00
        try:  # TODO: This should be handled be re-sending command
            unit_code = int(Brooks.get_bytes(0,data,1),16)
            pv = Brooks.ieee_unpack(Brooks.get_bytes(1,data,4))[0]
        except ValueError:
            pv = -1
            unit_code = 171  # Satisfy assertion check, we know what is wrong
        #assert unit_code == 171  # Flow unit should always be mL/min
        return pv

    def read_flow_range(self, select_code=1): #command #151 for SLA-series
        """ c.f. *SLA document* page (64), section 8-6 Command #151 Read
        Gas Density, Flow Reference and Flow Range.
        
        Read the density of the selected gas, the operational flow range
        and the reference temperature and pressure for the flow range.
        The flow range equals the volume flow in engineering units at 100%
        as calibrated. The reference temperature and pressure are the
        conditions at which the volume flow is specified.

        Args:
            select_code: Gas Selection Code (1-6)

        Returns:
            `reference_flow_range_value` (float), 
            `reference_flow_unit_code` (unsigned int).
        """

        byte0 = hex(select_code)[2:].zfill(2)
        status, data = self.comm2('97' + byte0 + '01') #Command 151, select_code 1, len 1
        try:  # TODO: This should be handled be re-sending command
            gas_selection_code = int(Brooks.get_bytes(0,data,1),16)
            density_unit_code = int(Brooks.get_bytes(1,data,1),16)
            process_gas_density = Brooks.ieee_unpack(Brooks.get_bytes(2,data,4))[0]
            reference_temperature_unit_code = int(Brooks.get_bytes(6,data,1),16)
            reference_temperature_value = Brooks.ieee_unpack(Brooks.get_bytes(7,data,4))[0]
            reference_pressure_unit_code = int(Brooks.get_bytes(11,data,1),16)
            reference_pressure_value = Brooks.ieee_unpack(Brooks.get_bytes(12,data,4))[0]
            unit_code = int(Brooks.get_bytes(16,data,1),16) #reference_flow_unit_code
            flow_range = Brooks.ieee_unpack(Brooks.get_bytes(17,data,4))[0] #reference_flow_range_value
        except ValueError:
            flow_range = -1
            unit_code = 171  # Satisfy assertion check, we know what is wrong
        #assert unit_code == 171  # Flow unit should always be mL/min
        return flow_range, unit_code

    def read_setpoint(self): #command 235
        """ c.f. *SLA document* page (86), section 8-30 Command #235 
        Read Setpoint in % and Selected Units.
        
        Read the current setpoint value in percent of full scale and in 
        selected units. The setpoint in selected units compared to its 
        full scale range should be the equivalent of the setpoint in 
        percent.

        Returns:
            `setpoint`(float) in % , 
            `selected_unit_code` (unsigned int).

        """
        status, data = self.comm2('eb00') # command = eb byte count = 00
        #percent_unit = int(Brooks.get_bytes(0,data,1),16) #always 57 (39 hex)
        #setpoint_percent = Brooks.ieee_unpack(Brooks.get_bytes(1,data,4))[0]
        select_unit = int(Brooks.get_bytes(5,data,1),16) # 250 (FA), etc.
        setpoint = Brooks.ieee_unpack(Brooks.get_bytes(6,data,4))[0]
        return setpoint, select_unit

    def read_totalizer_status(self): #command 240
        """ c.f. *SLA document* page (89), section 8-33 Command #240 
        Read Totalizer Status.
        
        Read the totalizer status. Both the totalizer status and the 
        selected totalizer unit is returned.

        Returns:
            `totaliser_status`(unsigned int), see section 9-14 (p.102). 
                0 (stop/stopped), 1 (start.running), 2 (reset/resetting)
            `totaliser_unit` (unsigned int), see setpoint unit.
                57(decimal percent) or 250(decimal, same unit as flowrate measurement)

        """
        status, data = self.comm2('f000') # command = f0, byte count = 00
        totaliser_status = int(Brooks.get_bytes(0,data,1),16)
        totaliser_unit = int(Brooks.get_bytes(1,data,1),16)
        return totaliser_status, totaliser_unit
        
    def read_totalizer(self): #command 242
        """ c.f. *SLA document* page (90), section 8-35 Command #242 
        Read Totalizer Value and Unit.

        Read the totalizer counter and the totalizer unit. The totalizer 
        unit is dependent on the selected flow unit and can not be 
        selected separately.
        
        Returns:
            `totaliser_count`(float). 
            `totaliser_unit` (unsigned int), see setpoint unit.
                57(decimal percent) or 250(decimal, same unit as flowrate measurement)

        """
        status, data = self.comm2('f200') # command = f2, byte count = 00
        totaliser_unit = int(Brooks.get_bytes(0,data,1),16)
        totaliser_count = Brooks.ieee_unpack(Brooks.get_bytes(1,data,4))[0]
        
        return totaliser_count, totaliser_unit
        
        #TODO def totalizers: commands 240-242 (p.89-92)

    def set_totalizer(self, cmd_code=0): #command #241
        """ c.f. *SLA document* page (90), section 8-34 Command #241 
        Set Totalizer Control.
        
        Set the totalizer state. Use this command to start, stop or 
        reset the totalizer. Actually, the totalizer has only two states;
        running and stopped. A totalizer reset will not effect the 
        totalizer state.
        
        Args:
            cmd_code: Totalizer command/status codes. Refer to Section 9-14 (p. 102).
                0(stop/stopped); 1(start/running); 2(reset/resetting).
               

        Returns:
            `totaliser_status`(unsigned int), see section 9-16 (p.102).

        """
        byte0 = hex(cmd_code)[2:].zfill(2)
        status, data = self.comm2('f101' + byte0)
        totaliser_status = int(Brooks.get_bytes(0,data,1),16)
        return totaliser_status

    def set_flow(self, flowrate, unit_code=250): #command #236
        """ c.f.: *SLA document* page (87), section 8-31 Command #236 
        Write Setpoint in % or Selected Units.
        
        Write the current setpoint value in percent of full scale or in 
        selected units to the device. If the setpoint unit code is set 
        to percent (code 57) the setpoint value is assumed to be in 
        percent. If the setpoint unit code is set to Not Used, the 
        setpoint value is assumed to be in the selected unit. The return 
        message is the same as the one of Command #235. The setpoint in 
        selected units compared to its full scale range should be the 
        equivalent of the setpoint in percent. When this command is 
        received, the Setpoint Source will be set to digital automatically
        if not already in digital mode. The Setpoint Source will remain in 
        digital mode until the user returns the Setpoint Source to analog 
        mode via Command #216 or until the power to the device is cycled.

        *N.B.*  Setpoint and setpoint units must be appropriate for the 
        type of control the device is configured to perform, flow or pressure.

        Args:
            flowrate: Setpoint value. In either percent of full scale or in 
            selected units.
            unit_code: Setpoint unit. 57 (decimal), “Percent” or 250 
            (decimal) “Not Used”.
            
        Returns:
            `setpoint`(float) in %, 
            `selected_unit_code` (unsigned int), 
        """
        ieee_flowrate = Brooks.ieee_pack(flowrate)
        #ec05: ec = cmd 236; 05 = len(unit_code + ieee_sp)
        #39 (57 dec) = unit code for percent; FA (250 dec)= unit code for 'same unit as flowrate measurement'
        status, data = self.comm2('ec05' + 'FA' + ieee_flowrate)
        #percent_unit = int(Brooks.get_bytes(0,data,1),16) #always 57 (39 hex)
        #setpoint_percent = Brooks.ieee_unpack(Brooks.get_bytes(1,data,4))[0]
        select_unit = int(Brooks.get_bytes(5,data,1),16) # 17(l/min), 240(cc/min), etc.
        setpoint = Brooks.ieee_unpack(Brooks.get_bytes(6,data,4))[0]
        return setpoint, select_unit

    def select_flow_unit(self, flow_unit, flow_ref=0): #command #196
        """ c.f. *SLA document* page (73), section 8-16 Command #196 
        Select Flow Unit.

        Select a flow unit. Selecting a flow unit not only consists of 
        selecting the flow unit, but also the reference condition. The 
        selected flow unit will be used in the conversion from flow data. 
        Flow data will be made available to the user in the selected 
        flow unit and reference conditions. (See Section 5-2-1.)

        Args:
            flow_unit: Selected flow unit. Refer to Section 9-3, Flow rate
            unit and reference codes.            
            flow_ref: Selected flow reference. Refer to Section 9-3, Flow 
            rate unit and reference codes.

        Returns:
            True if successful else False. 
        """
        byte0 = hex(flow_ref)[2:].zfill(2)
        byte1 = hex(flow_unit)[2:].zfill(2)
        status, data = self.comm2('c402' + byte0 + byte1)
        flag = byte0 == data[:2] and byte1 == data[2:]
        return flag

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
