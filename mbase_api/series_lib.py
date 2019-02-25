# -*- coding: utf-8 -*-
"""
Created on Tue Sep 11 09:40:05 2018

@author: danie
"""
import numpy as np

class xy_series(object):
    
    def __init__(self,x_array,y_array,x_label="x",y_labels = "y",NoData=-999,decimals=1):
        self.decimals = decimals
        self.x_array = x_array
        self.y_array = y_array.round(decimals=decimals)
        self.x_label = x_label
        self.y_labels = y_labels
        self.x_gctype = "number"
        self.y_gctype = "number"
        self.NoData = NoData
        
    
    def toGDT(self,min_val=-99999,max_val=99999):
        header = []
        header.append({"label": self.x_label, "type":self.x_gctype})
        for y_label in self.y_labels:
            header.append({"label": y_label, "type":self.y_gctype})
            
        rows = []
        for idx, x in enumerate(self.x_array):
            cols = []
            cols.append({"v":float(x)})
            for idy in range(0,self.y_array.shape[0]):
                value = None
                if not np.isnan(float(self.y_array[idy,idx])) and min_val <= float(self.y_array[idy,idx]) <= max_val:
                    value = float(self.y_array[idy,idx])  
                cols.append({"v":value })
            rows.append({'c':cols})
        
        return {"cols":header,"rows":rows}