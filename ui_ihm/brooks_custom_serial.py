import sys
sys.path.append('..')
from brooks_s_protocol_backend_serial import Brooks

import numpy as np

def unit_code_to_string(unit_code_or_str, reverse=False):
    codes = {17: 'l/min', 
                    171: 'ml/min',
                    240: 'cc/min'}
    if reverse:
        assert unit_code_or_str in codes.values() #see section 9-3
        return [k for k, v in codes.items() if v == unit_code_or_str][0]
    else:
        assert unit_code_or_str in codes.keys()
        return codes[unit_code_or_str]

class BrooksCustom(Brooks):
    numInstances = 0

    def __init__(self, tag, uartdriver):
        """

        Args:
            tag: 8 digits tag number of MFC
            port: comport
        """
        super(BrooksCustom, self).__init__(tag, uartdriver)
        self.count()
        self.data_desc = ['unit', 'fs', 'sp', 'pv']
        self.raw_data = {}
        for desc in self.data_desc:
            self.raw_data[desc] = None

    @classmethod
    def count(cls):
        cls.numInstances += 1

    def get_all_data(self):
        """ (fs, unit) + (sp, unit) + pv """

        self.raw_data[self.data_desc[1]], ref_unit_code = self.read_flow_range()
        self.raw_data[self.data_desc[2]], unit_code = self.read_setpoint()
        self.raw_data[self.data_desc[0]] = unit_code_to_string(unit_code)
        self.raw_data[self.data_desc[3]] = self.read_flow()
        return self.raw_data
    
    def get_pv(self):
        self.raw_data[self.data_desc[3]] = self.read_flow()
        return self.raw_data[self.data_desc[3]]

    def set_unit(self, unit_str, flow_ref=0):
        unit_code = unit_code_to_string(unit_str, True)
        #à reformater unit car il y a une espace devant
        return self.select_flow_unit(unit_code, flow_ref)

    def set_setpoint(self, sp, unit_code=250):
        sp_out, select_unit = self.set_flow(sp, unit_code)
        return True if np.isclose(sp, sp_out, atol=1e-5) else False
