import numpy as np
import random

class Doomy:
    def __init__(self):
        random.seed()
        self.data_desc = ['unit', 'fs', 'sp', 'pv']
        self.flow_units = ['l/min', 'ml/min','cc/min']
        self.raw_data = {}
        for desc in self.data_desc:
            self.raw_data[desc] = None
        
        self.raw_data[self.data_desc[0]] = random.sample(self.flow_units*10,1)[0]
        self.raw_data[self.data_desc[1]] = random.randint(5, 20)
        #self.raw_data[self.data_desc[2]] = 0.0
        self.raw_data[self.data_desc[2]] = self.raw_data[self.data_desc[1]]/random.randint(5, 20)
        self.raw_data[self.data_desc[3]] = 0.0

    def get_all_data(self):
        #self.raw_data[self.data_desc[2]] = self.raw_data[self.data_desc[1]]/random.randint(5, 20)
        #self.raw_data[self.data_desc[3]] =  self.raw_data[self.data_desc[2]] + random.random()/50
        self.get_pv()
        return self.raw_data
    
    def get_pv(self):
        self.raw_data[self.data_desc[3]] = self.raw_data[self.data_desc[2]] + random.random()/50
        return self.raw_data[self.data_desc[3]]

    def set_unit(self, unit):
        assert unit.strip() in self.flow_units
        self.raw_data[self.data_desc[0]] = unit.strip()
        return self.raw_data[self.data_desc[0]]

    def set_setpoint(self, sp):
        assert sp <= self.raw_data[self.data_desc[1]]
        self.raw_data[self.data_desc[2]] = sp
        return True if sp == self.raw_data[self.data_desc[2]] else False

    def set_fs(self, fs):
        self.raw_data[self.data_desc[1]] = fs
        return True
