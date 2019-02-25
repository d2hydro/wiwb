# -*- coding: utf-8 -*-
"""
Python library for statistic functions. Including:
- GEV and GEV inverse
"""

__author__ = "Daniel Tollenaar"
__credits__ = ["Daniel Tollenaar", "Siebe Bosch"]
__maintainer__ = "Daniel Tollenaar"
__email__ = "daniel@d2hydro.nl"
__status__ = "Development"

import numpy as np


def GEVCDF(mu, sigma, Zeta,X):
    """
    Datum: 9-11-2010
    Auteur: Siebe Bosch(Python implementatie: Daniel Tollenaar)
    Deze routine berekent de ONDERschrijdingskans van een bepaalde parameterwaarde volgens de GEV-verdeling (Gegeneraliseerde Extreme Waarden)
    dit betekent gewoon dat we de verdelingsfunctie gaan berekenen (= de integraal van de kansdichtheidsfunctie)
    """
    X = np.array(X, dtype=np.float)
    e = np.exp(1) 
    
    t = np.zeros((len(X),len(mu)),dtype=float)
    for idx, x in enumerate(X):
        Z = (x - mu) / sigma
        for idy, zeta in enumerate(Zeta):
            z = Z[idy]
            if zeta == 0: t[idx,idy] = e ** -z
            else: t[idx,idy] = (np.float(1) + zeta * z) ** (np.float(-1) / zeta)
  
    return e ** (-1 * np.array(t))

def GEVINVERSE(mu, sigma, Zeta, X):
    """
    Datum: 9-11-2010
    Auteur: Siebe Bosch (Python implementatie: Daniel Tollenaar)
    Deze routine berekent de ONDERschrijdingskans p van een bepaalde parameterwaarde volgens GEV-verdeling
    dit betekent gewoon dat we de verdelingsfunctie gaan berekenen (= de integraal van de kansdichtheidsfunctie)
    """
    
    X = np.array(X, dtype=np.float)
    
    t = np.zeros((len(X),len(mu)),dtype=float)
    for idx, x in enumerate(X):
        t[idx] = mu + sigma * (((np.float(-1) * np.log(x)) ** (np.float(-1) * Zeta) - np.float(1)) / Zeta)
        
    return t

def GLOCDF(mu, sigma, Teta, X):
    """
    Datum: 5-11-2018
    Auteur: Siebe Bosch (Python implementatie: Daniel Tollenaar)
    Deze routine berekent de ONDERschrijdingskans van een bepaalde parameterwaarde volgens de GLO-verdeling (Generalized Logistic)
    dit betekent gewoon dat we de verdelingsfunctie gaan berekenen (= de integraal van de kansdichtheidsfunctie)
    """
  
    X = np.array(X, dtype=np.float)
    
    t = np.zeros((len(X),len(mu)),dtype=float)
    
    for idx, x in enumerate(X):
        Z = (x - mu) / sigma
        for idy, teta in enumerate(Teta):
            z = Z[idy]
            if teta == 0: t[idx,idy] = (1 + np.exp(-z)) ** -1
            else: t[idx,idy] = (1 + (1 - teta * z) ** (1 / teta)) ** -1
    return t

def GLOINVERSE(mu, sigma, Teta, X):
    """
    Datum: 24-12-2018
    Auteur: Siebe Bosch (Python implementatie: Daniel Tollenaar)
    Deze routine berekent de waarde X gegeven een ONDERschrijdingskans en een GLO-kansverdeling (Generalized Logistic)
    dit betekent gewoon dat we de verdelingsfunctie gaan berekenen (= de integraal van de kansdichtheidsfunctie)
    """
    
    X = np.array(X, dtype=np.float)
    
    t = np.zeros((len(X),len(mu)),dtype=float)
    for idx, x in enumerate(X):
        for idy, teta in enumerate(Teta):
            if teta == 0: t[idx,idy] = mu[idy] - sigma[idy] * np.log(1 / x - 1)
            else:t[idx,idy] = mu[idy] + sigma[idy] * ((1 - (1 / x - 1) ** teta) / teta)
            
    return t