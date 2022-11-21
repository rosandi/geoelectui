#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#---------------------------------------------------------
# Program to operate Geoelectric Prototype 
# Prototype Instrument Code: GeoPhy IGF-02 Geoelectric
#
#  (c) Rosandi, 2020
#---------------------------------------------------------

from time import sleep
from datetime import datetime as dt
import sys
import json
import numpy as np
from math import isnan
from threading import Thread, Event

# ----------- VARIABLES -----------

maxlayer=3
msrthread_id=None
msrev=Event()
current_control=Event()
abort=False

pp=0
pm=0
vp=0
vm=0

### TUNABLE PARAMETERS ###

devcfg = {
    'crange': (0.025,50.0),
    'injection_low_pwm': 20,
    'injection_pwm_increment': 5,
    'injection_volt_limit': 400,
    'injection_volt_low': 18,
    'injection_max_try': 50,
    'voltage_limit': 4966.0,
    'max_measurement_try': 10,
    'filename_prefix': 'data-'
}

nan=float('nan');

##### COMMAND LINE PARAMETERS ####
#
# macOS: /dev/cu.wchusbserial1420
# Linux: /dev/ttyUSB0 or /dev/ttyACM0

comm='/dev/ttyUSB0'
speed=9600

boxarr=[] # box figure array (color, values, etc)
proarr=[] # probe position (surface)
resarr={} # measured resistivity array
probres={} # interprobe resistances
rmin=0
rmax=0
firsttake=True
probres_avail=False
logstring=''

def plog(s):
    global logstring
    logstring+='\n'+s
    print(s)

def adjust_measure(crange, ntry=devcfg['injection_max_try']):
    ip=0.0
    nt=0
    vol=0

    while not (ip>crange[0] and ip<crange[1]):

        if not msrev.is_set():
            break
    
        if ip<crange[0]:
            g.incr_injection(devcfg['injection_pwm_increment'])
        elif ip>crange[1]:
            g.decr_injection(devcfg['injection_pwm_increment'])

        ip=g.measure_current()
        vol=g.measure_injection()
        
        if vol>devcfg['injection_volt_limit']:
            plog(f'injection limit exceeded {vol}V')
            break
            
        plog("injection: %0.3EmA at %0.3EV (I_limit: %0.3f,%0.3f)"%(ip,vol,crange[0],crange[1]))
        
        nt+=1
        if nt>ntry:
            plog("maximum try...")
            break

    sleep(g.WAIT2)

    ip=g.measure_current()
    meter_vol=g.measure_voltage()

    return ip, meter_vol, vol

#   ------- UNTESTED ------
def currentclamp():
    # call this with thread!

    ip=measure_current()
    while current_control.is_set():
        ap=measure_current()
        if ap < ip:
            g.incr_injection()
        elif ap>ip:
            g.decr_injection()

def hold_current():
    global curtrd

    current_control.set()
    curtrd=Thread(target=currentclamp)
    curtrd.start()

def release_current():
    current_control.clear()
    curtrd.join()

# ----------------------------

def set_conf(cfg):
    global pconf,resarr, probres, firsttake, probres_avail, devcfg

    pconf=cfg
    firsttake=True
    probres_avail=False
    logstring=''

    if 'device_configuration' in cfg:
        cc=cfg['device_configuration']

        if cc:
            for c in cc:
                devcfg[c]=cc[c]

    resarr={}

    for p in pconf['conf']:
        resarr[tuple(p[0])]=(p[0], None)

    for p in range(1,pconf['nprobe']):
        '''probres format: (resistance, injection_voltage, injection_current)'''
        probres[p,p+1]=None

def custom_measurement():  # pc is the probe configuration dict
    '''read configuration from file'''

    global rmin,rmax, pm,pp,vm,vp, logstring, abort
    
    if not pconf: return

    # clear previous measurement data
    for p in resarr:
        resarr[p]=(p, None)

    if pconf['nprobe'] != g.NPROBE:
        plog('incompatible configuration: probe {} <-> {}'.format(pconf['nprobe'], nprobe))
        return
    
    rmin,rmax=1e6,0

    abort=False

    # use previous voltage to discharge
    prevolt=devcfg['injection_volt_low']

    for p in pconf['conf']:

        if not msrev.is_set(): 
            plog('measurement aborted')
            abort=True
            break;

        pm=p[1][0]
        pp=p[1][1]
        vm=p[1][2]
        vp=p[1][3]

        plog("> {} probe conf: pm={} pp={} vm={} vp={}".format(p[0],pm,pp,vm,vp))
        
        ntry=0
        g.discharge(prevolt,verbose=True)

        while ntry<devcfg['max_measurement_try']:

            if not msrev.is_set(): 
                plog('measurement aborted')
                abort=True
                break;

            ntry+=1
            
            # 1. discharge
            g.probe_off()
            g.inject(False)
            #g.discharge(devcfg['injection_volt_low'],verbose=True)
            sleep(g.WAIT)
            
            # 2. measure self potential
            g.probe(0,0,vm,vp)
            sv=g.measure_voltage()

            if sv>devcfg['voltage_limit']:
                plog(f'volt measurement limit (sv)')
                g.probe_off()
                break
            
            # 3. current injection and measurement

            g.inject(False)  # release first
            sleep(g.WAIT)

            g.probe(pm,pp,vm,vp)
            g.set_injection(prevolt)
            g.inject()

            mi,mv,prevolt=adjust_measure(devcfg['crange'])

            if mv>devcfg['voltage_limit']:
                plog(f'volt measurement limit {mv}... retrying...')
                g.probe_off()
                continue
           
            if mi!=0.0:
                mr=abs((mv-sv)/mi)
                if rmin>mr: rmin=mr
                if rmax<mr: rmax=mr
            else:
                mr=float('nan')

            resarr[tuple(p[0])]=(p[0], [mv,mi,mr,sv])
            plog("R=%0.2EOhm V=%0.2EmV C_inj=%0.2EmA V_self=%0.2EmV"%(mr,mv,mi,sv))
            break
        
    g.probe_off()   # turn off relays
    g.inject(False)
    g.discharge(devcfg['injection_volt_low'])
    g.flush()
    pm,pp,vm,vp=0,0,0,0
    msrev.clear()
    saveData()

def measure_resistances():
    global probres, logstring, probres_avail

    for pr in probres:
        probres[pr]=None

    logstring=''
    
    for p in range(1, pconf['nprobe']):

        if not msrev.is_set(): break
        
        g.discharge(devcfg['injection_volt_low'])
        sleep(g.WAIT2)
        g.set_injection(devcfg['injection_low_pwm'])
        g.probe(p,p+1,0,0)
        
        I=g.measure_current()
        V=g.measure_injection()
        S=g.measure_shunt()
        
        try:
            probres[p,p+1]=((V+S)/I,V+S,I)
        except:
            probres[p,p+1]=(nan,V+S,I)

        plog('I=%0.4f V=%0.4f S=%0.2f'%(I,V,S))
        g.inject(False)
        sleep(0.2)
        g.shift()
        g.inject()
        
    g.probe_off()   
    msrev.clear()
    probres_avail=True

def resmap(p, clr):
    nn=len(clr)
    
    if rmax == rmin:
        return 0
    
    vv=resarr[p][1]
    if vv:
        if not isnan(vv[2]):
            c=1+int(nn*(vv[2]-rmin)/(rmax-rmin))
        else:
            c=0
    else:
        c=0

    # just in case
    if c<0: c=0
    if c>=nn: c=nn-1
    return c

def saveData():
    try:
        fnm=devcfg['filename_prefix']+str(int(dt.timestamp(dt.now())))+'.json'
        plog(f'saving data to {fnm}')
        jdata={ 
                'comment':'Geoelectric measurement data\nrosandi, 2020\n'+
                'Geophysics Universitas Padjadjaran',
                'measurement_fields': '[cell_i, cell_j], [V, I, R, V_self]'
            }

        if abort:
            jdata['measurement_status']='aborted'
        else:
            jdata['measurement_status']='success'

        vres=[]
        for a in resarr: vres.append(resarr[a])
        jdata['data']=vres

        if probres_avail:
            pres=[]
            for a in probres: pres.append([a,probres[a]])
            jdata['probe_resistance_fields']='[prob_i, prob_j], [R, V, I]'
            jdata['probe_resistance']=pres
        
        jdata['conf']=pconf
        
        with open(fnm,'w') as fl:
            json.dump(jdata,fl)

    except Exception as e:
        print(e)
        plog('saving data failed')
   
def init_dev(comm,speed,cal=True):
    global g

    try:
        plog('initialize...')
        import gelec as g
        g.init(comm,speed)
        
        if cal:
            plog('calibrating...')
            plog(f'calibration parameters:  {g.soft_calibrate(n=5,verbose=True)}')

        plog('device ready')
    
    except Exception as e:
        print(e)
        import gelecdummy as g
        g.init('null')
    
    g.set_naverage(20)
    g.plog=plog

    

##########################
###### MAIN PROGRAM ######
##########################

if __name__ == "__main__":
    
    for arg in sys.argv:
        if arg.find('comm=') == 0:
            comm=arg.replace('comm=','')
        if arg.find('speed=') == 0:
            speed=int(arg.replace('speed=',''))

    if not comm:
        print("arguments required: comm=[comm-port]")
        exit(-1)
    
    init_dev(comm, speed, cal=False)

     # don't forget to initialize first
   
    try:
        while True:
            cmdln=input('GE-CTR > ')
            
            if cmdln.find('q') == 0:
                g.close()
                break
            
            elif cmdln.find('probe')==0:
                prb=cmdln.split()
                if len(prb)==5:
                    g.probe(int(prb[1]), int(prb[2]), int(prb[3]), int(prb[4]))
                else:
                    g.probe_off()

            elif cmdln.find('conf') == 0:
                confile=cmdln.replace('conf=','')

            elif cmdln.find('acq') == 0:
                custom_measurement(confile)

            elif cmdln.find('mres') == 0:
                measure_resistance()

            elif cmdln.find('discharge')==0:
                g.discharge(0,ntry=10,verbose=True)

            elif cmdln.find('inject')==0:
                cmdln=cmdln.split()
                if 'off' in cmdln:
                    g.inject(False)
                else:
                    g.inject(True)

            elif cmdln.find('calv')==0:
                # calv true_value
                vtrue=float(cmdln.split()[1])
                g.cal_vinj()
                print(g.get_devinfo())

            elif cmdln.find('flush')==0:
                print(g.flush())

            else:
                print(f'send "{cmdln}" to device')
                print(g.send(cmdln))
                   
    except KeyboardInterrupt:
        print('terminating')
    except:
        print('program error')
        raise

