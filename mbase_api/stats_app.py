# -*- coding: utf-8 -*-
"""
Python app for Meteo Base. Handling computation of duration curves
"""

__author__ = "Daniel Tollenaar"
__credits__ = ["Daniel Tollenaar", "Siebe Bosch"]
__maintainer__ = "Daniel Tollenaar"
__email__ = "daniel@d2hydro.nl"
__status__ = "Development"

from collections import defaultdict
from flask import (
    Blueprint, request
)
from json import dumps
from mbase_api.stats_lib import GEVCDF, GEVINVERSE, GLOCDF, GLOINVERSE
from mbase_api.series_lib import xy_series
from numpy import array, log, log10, nan, exp
import os
import xlrd

DURATION = {"STOWA2015":[2, 4, 8, 12, 24, 48, 96, 192, 216],"STOWA2018":[1/6,1/4,1/2,1,2,4,8,12]}
VOLUMES = [10,20,30,40,50,75,100,150,200,250]
RETURN_PERIODS = {"STOWA2015":[2,10,25,50,100,200,500,1000,10000],"STOWA2018":[0.5,1,2,5,10,20,25,50,100,200,250,500,1000,10000]}
study = 'STOWA2015'

bp = Blueprint('stats', __name__, url_prefix='/api/stats')

# set working directory
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

# get params
wb = xlrd.open_workbook(os.path.abspath(r'resources\Regenduurlijnparameters.xlsm'))
sh = [wb.sheet_by_index(0),wb.sheet_by_index(1)]

params = [defaultdict(list),defaultdict(list)]
for i in range(1,sh[0].nrows):
    climate = int(sh[0].cell(i,0).value)
    scenario = str(sh[0].cell(i,1).value)
    region = str(sh[0].cell(i,2).value)
    season = str(sh[0].cell(i,3).value)
    values = ()   
    params[0][climate,scenario,region,season].append([sh[0].cell(i,j).value for j in range(4,10)])

for i in range(1,sh[1].nrows):
    climate = int(sh[1].cell(i,0).value)
    scenario = str(sh[1].cell(i,1).value)
    region = str(sh[1].cell(i,2).value)
    season = str(sh[1].cell(i,3).value)
    values = ()   
    params[1][climate,scenario,region,season].append([sh[1].cell(i,j).value for j in range(4,10)])

del wb

def get_GEV_params(climate,scenario,season,region,durations):      
    cp = params[0][int(climate),scenario,region,season][0]
    mu = (float(cp[0]) + float(cp[1]) * log(durations))**(1/float(cp[2]))
    gam = float(cp[3]) + float(cp[4]) * log(durations) + float(cp[5]) * log(durations)**2
    sigma = mu * gam
    Zeta = -(-0.090 + 0.017 * array(durations) / 24 )# alleen voor RD_X_ARRAY < 240 uur!
    
    return mu, sigma, Zeta

def get_GLO_params(climate,scenario,season,region,durations): 
#climate,scenario,season,region = '2014','-','jaarrond','-' 
    if len(params[1][int(climate),scenario,region,season]) > 0:  
        cp = params[1][int(climate),scenario,region,season][0]
        mu, sigma,teta = [],[],[] 
        for idx, duration in enumerate(durations):
            duration = float(duration)*60
            mu.append(float(cp[0])+float(cp[1])*log10(duration) +float(cp[2]) *log10(duration)**2)
            if duration <= 104:
                 sigma.append(mu[idx]*(0.04704+0.1978*log10(duration)-0.05729*log10(duration)**2))
            else:  sigma.append(mu[idx]*(0.2801-0.0333*log10(duration)))
            teta.append(cp[3]+ cp[4] *log10(duration) + cp[5] *log10(duration)**2)
        return mu, sigma, teta
    else: return False
    
@bp.route('/volume/<study>', methods=('POST', ))
def volume(study):
    """ return the Google Data Table in JSON from a html form set of parameters """
    # get params from html form
    climate = request.form['climate']
    try: scenario = request.form['scenario']
    except: scenario = '-'
    season = request.form['season']
    try: region = request.form['region']
    except: region ='-'
    try: vol = request.form['value']
    except: vol = ''
    #process volumes array
    vols = VOLUMES.copy()
    if not vol == '': vols = vols + [float(vol)]
        
    y_labels = []
    for volume in vols:
        y_labels.append('{} mm'.format(int(volume)))
    
    if study == 'STOWA2015':
        #get GEV params
        mu, sigma, Zeta = get_GEV_params(climate,scenario,season,region,DURATION[study])
        # compute GEVCDF
        gev = GEVCDF(mu, sigma, Zeta, vols)
        prob = 1/-log(gev)            

        result = xy_series(array(DURATION[study]), prob, x_label="duur (uren)",
                           y_labels=y_labels,decimals=1).toGDT(min_val=RETURN_PERIODS[study][0],max_val=RETURN_PERIODS[study][-1])
   
    if study == 'STOWA2018':
        vols = [vol/1.02 for vol in vols]
        GLO_params = get_GLO_params(climate,scenario,season,region,DURATION[study])
        if not GLO_params == False:
            mu, sigma, teta =   GLO_params  
            glo = GLOCDF(mu, sigma, teta, vols)
            prob = 1/-log(glo)
            # convert result to Google Data Table

            # convert result to Google Data Table
            result = xy_series(array(DURATION[study]).round(decimals=2), prob, x_label="duur (uren)",
                               y_labels=y_labels,decimals=1).toGDT(min_val=RETURN_PERIODS[study][0],max_val=RETURN_PERIODS[study][-1])
        else: result = GLO_params
    
    return dumps(result), 200

@bp.route('/returnperiod/<study>', methods=('POST', ))
def returnperiod(study):
    """ return the Google Data Table in JSON from a html form set of parameters """
    # get params from html form
    climate = request.form['climate']
    try: scenario = request.form['scenario'] 
    except: scenario = '-'
    season = request.form['season']
    try: region = request.form['region']
    except: region ='-'
    try: dur = request.form['value']
    except: dur = ''
    
    #process durations array
    durs = RETURN_PERIODS[study].copy()
    if not dur == '': durs = durs + [float(dur)]
    return_periods = exp(-1/array(durs))
    
    #process y-labels
    y_labels = []
    for duration in durs:
        y_labels.append('{} jr'.format(int(duration)))

    if study == 'STOWA2015':
        #get GEV params
        mu, sigma, Zeta = get_GEV_params(climate,scenario,season,region,DURATION['STOWA2015'])
        # compute GEVCDF
        vols = GEVINVERSE(mu, sigma, Zeta, return_periods)

        result = xy_series(array(DURATION[study]), vols, x_label="duur (uren)",
                       y_labels=y_labels,decimals=0).toGDT()
    
    if study == 'STOWA2018':
        y_labels[0] = '0.5 jr'
        #get GLO params
        GLO_params = get_GLO_params(climate,scenario,season,region,DURATION['STOWA2018'])
        if not GLO_params == False: 
            mu, sigma, teta =   GLO_params     
        # convert result to Google Data Table
            vols = GLOINVERSE(mu, sigma, teta, return_periods)
            vols = array([vol*1.02 for vol in vols])
        
            result = xy_series(array(DURATION[study]).round(decimals=2), vols, x_label="duur (uren)",
                           y_labels=y_labels,decimals=0).toGDT()
        else: result = GLO_params
        
    return dumps(result), 200
