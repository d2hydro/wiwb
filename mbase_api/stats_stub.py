# -*- coding: utf-8 -*-
"""
Created on Mon Oct 15 16:31:25 2018

@author: danie
"""
from collections import defaultdict
from numpy import log, array, float
import numpy as np

import os
import xlrd
from stats_lib import GEVCDF
from series_lib import xy_series

RD_X_ARRAY = [1, 2, 4, 8, 12, 24, 48, 96, 192, 216]

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

# get params
wb = xlrd.open_workbook(os.path.abspath(r'resources\KNMI_2014_GEV_parameters.xlsx'))
sh = wb.sheet_by_index(0)   

params = defaultdict(list)
for i in range(1,sh.nrows):
    climate = int(sh.cell(i,0).value)
    scenario = str(sh.cell(i,1).value)
    region = str(sh.cell(i,2).value)
    season = str(sh.cell(i,3).value)
    values = ()   
    params[climate,scenario,region,season].append([sh.cell(i,j).value for j in range(4,10)])

del wb

climate = 2014
scenario = ''
season = 'jaarrond'
region = ''
vval = '41'  

# hier komt de functie

cp = params[int(climate),scenario,region,season][0]


mu = (float(cp[0]) + float(cp[1]) * log(RD_X_ARRAY))**(1/float(cp[2]))
gam = float(cp[3]) + float(cp[4]) * log(RD_X_ARRAY) + float(cp[5]) * log(RD_X_ARRAY)**2
sigma = mu * gam
Zeta = -(-0.090 + 0.017 * array(RD_X_ARRAY) / 24 )# alleen voor RD_X_ARRAY < 240 uur!

## functie
if not vval == '':
    volumes = [50,70,90] + [float(vval)]

GEV = GEVCDF(mu, sigma, Zeta,volumes)

POE = 1/(1-GEV)

y_labels = []
for volume in volumes:
    y_labels.append('{} mm'.format(int(volume)))

result = xy_series(RD_X_ARRAY, POE, x_label="duur (uren)",
                       y_labels=y_labels).toGDT()



#rd_y_array = GEVCDF(mu, sigma, zeta, array(RD_X_ARRAY))