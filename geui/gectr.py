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
import numpy as np
from threading import Thread, Event

# ----------- VARIABLES -----------

maxlayer=3
msrthread_id=None
msrev=Event()
pp=0
pm=0
vp=0
vm=0

### TUNABLE PARAMETERS ###

devcfg = {
    'crange': (0.025,50.0),
    'injection_low_pwm': 20,
    'injection_pwm_increment': 5,
    'injection_volt_limit': 200,
    'injection_volt_low': 15,
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

comm='COM5'
#comm='/dev/ttyUSB0'
speed=9600

boxarr=[] # box figure array (color, values, etc)
proarr=[] # probe position (surface)
resarr={} # measured resistivity array
probres={} # interprobe resistances
rmin=0
rmax=0
firsttake=True

def adjustcurrent(crange, ntry=devcfg['injection_max_try']):
    ip=0.0
    nt=0
        
    while not (ip>crange[0] and ip<crange[1]):  
        if not msrev.is_set():
            break
    
        ip=g.measure_current();
        if ip<crange[0]:
            g.incr_injection(devcfg['injection_pwm_increment'])
        elif ip>crange[1]:
            g.decr_injection(devcfg['injection_pwm_increment'])
        vol=g.measure_injection()
        
        if vol>devcfg['injection_volt_limit']:
            break
            
        print("injection: %0.4fmA at %0.3fV (curr_limit: %0.3f,%0.3f)"%(ip,vol,crange[0],crange[1]))
        
        nt+=1
        if nt>ntry:
            print("max try number reached")
            break
        
    return ip

def set_conf(cfg):
    global pconf,resarr, probres, firsttake

    pconf=cfg
    firsttake=True

    resarr={}

    for p in pconf['conf']:
        resarr[tuple(p[0])]=(p[0], None)

    for p in range(1,pconf['nprobe']):
        '''probres format: (resistance, injection_voltage, injection_current)'''
        probres[p,p+1]=None

def custom_measurement():  # pc is the probe configuration dict
    '''read configuration from file'''

    global rmin,rmax, pm,pp,vm,vp
    
    if not pconf: return

    # clear previous measurement data
    for p in resarr:
        resarr[p]=(p, None)

    if pconf['nprobe'] != g.NPROBE:
        print('incompatible configuration: probe {} <-> {}'.format(pconf['nprobe'], nprobe))
        return
    
    rmin,rmax=1e6,0

    for p in pconf['conf']:

        if not msrev.is_set(): 
            print('measurement aborted')
            break;

        pm=p[1][0]
        pp=p[1][1]
        vm=p[1][2]
        vp=p[1][3]

        print("> {} probe conf: pm={} pp={} vm={} vp={}".format(p[0],pm,pp,vm,vp))
        
        # measure self potential. FIXME! statistics
        g.discharge(devcfg['injection_volt_low'],verbose=True)
        sleep(g.WAIT)
        g.probe(0,0,vm,vp)
        sv=g.measure_voltage()
        
        ntry=0
        if ntry<devcfg['max_measurement_try'] and sv>=devcfg['voltage_limit']:
            ntry+=1
            print('bad probe contact (V_self).. retrying..')
            continue
            
        # injection
        g.inject(False)
        sleep(g.WAIT)

        g.probe(pm,pp,vm,vp)
        g.set_injection(devcfg['injection_low_pwm'])
        g.inject()
        sleep(g.WAIT)
        
        mi=0.0
        mi=adjustcurrent(devcfg['crange'])
        mv=g.measure_voltage()

        ntry=0
        if ntry<devcfg['max_measurement_try'] and mv>=devcfg['voltage_limit']:
            ntry+=1
            print('bad probe contact.. retrying...')
            continue
        
        if mi!=0.0:
            mr=np.abs((mv-sv)/mi)
            if rmin>mr: rmin=mr
            if rmax<mr: rmax=mr
        else:
            mr=float('nan')

        resarr[tuple(p[0])]=(p[0], [mv,mi,mr,sv])
        print("R=%0.2fOhm V=%0.3fmV C_inj=%0.4fmA V_self=%0.3fmV"%(mr,mv,mi,sv))
    
    g.probe_off()   # turn off relays
    g.discharge(devcfg['injection_volt_low'])
    g.flush()
    pm,pp,vm,vp=0,0,0,0
    msrev.clear()

def measure_resistances():
    global probres

    for pr in probres:
        probres[pr]=None
    
    for p in range(1, pconf['nprobe']):

        if not msrev.is_set(): break
        
        g.discharge(10.0)
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

        print('I=%0.4f V=%0.4f S=%0.2f'%(I,V,S))
        g.inject(False)
        sleep(0.2)
        g.shift()
        g.inject()
        
    g.probe_off()   
    msrev.clear()

def resmap(p, clr):
    nn=len(clr)
    
    if rmax == rmin:
        return 0
    
    vv=resarr[p][1]
    if vv:
        c=1+int(nn*(vv[2]-rmin)/(rmax-rmin))
    else:
        c=0

    # just in case
    if c<0: c=0
    if c>=nn: c=nn-1
    return c

def saveData():
    fl=open(devcfg['filename_prefix']+str(int(dt.timestamp(dt.now()))),'w')
    
    jdata={'comment':'Geoelectric measurement data\nrosandi, 2020'+
            'Geophysics Universitas Padjadjaran\n'+
            'fields: volt curr res vself conf'}

    for a in resarr:
        for b in a:
            fl.write(str(b)+'\n')
    fl.close()

   
def saveRes():
    fl=open(devcfg['filename_prefix']+'res-'+str(int(dt.timestamp(dt.now()))),'w')
    fl.write('# resistance measurement data\n')
    fl.write('# rosandi, 2020\n')
    fl.write('# Geophysics Universitas Padjadjaran\n')
    for a in range(len(probres)):
        fl.write(str((a+1,a+2)+probres[a])+'\n')
    fl.close()

def init_dev(comm,speed):
    global g

    try:
        import gelec as g
        g.init(comm,speed)
        print('calibrating...')
        print('calibration parameters: ', g.soft_calibrate(n=5,verbose=True))
    except:
        import gelecdummy as g
        g.init('null')

    g.set_naverage(20)

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
    
    init_dev(comm, speed)

     # don't forget to initialize first
   
    try:
        while True:
            cmdln=input('GE-CTR > ')
            
            if cmdln.find('q') == 0:
                g.close()
                break

            elif cmdln.find('conf') == 0:
                confile=cmdln.replace('conf=','')

            elif cmdln.find('acq') == 0:
                custom_measurement(confile)

            elif cmdln.find('mres') == 0:
                measure_resistance()

            else:
                print('send command directly to device')
                pass

                   
    except KeyboardInterrupt:
        print('terminating')
    except:
        print('program error')
        raise

