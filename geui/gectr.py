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
from threading import Thread, Event
import gelec as g

# ----------- VARIABLES -----------

maxlayer=3
msrthread_id=None
msrev=Event()
pp=0
pm=0
vp=0
vm=0

# device settings
nprobe=15

### TUNABLE PARAMETERS ###

rrange={'low':10.0,'high':10.0}
crange=(0.025,50.0)
injection_low_pwm=20
injection_pwm_increment=5
injection_volt_limit=200
injection_volt_low=15
injection_max_try=50
voltage_limit=4966.0
max_measurement_try=10
repeat_measurement=1
filename_prefix='data-'
gfactor=1.0
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
probres=[] # interprobe resistances

def adjustcurrent(crange, ntry=injection_max_try):
    ip=0.0
    nt=0
        
    while not (ip>crange[0] and ip<crange[1]):  
        if not msrev.is_set():
            break
    
        ip=g.measure_current();
        if ip<crange[0]:
            g.incr_injection(injection_pwm_increment)
        elif ip>crange[1]:
            g.decr_injection(injection_pwm_increment)
        vol=g.measure_injection()
        
        if vol>injection_volt_limit:
            break
            
        print("injection: %0.4fmA at %0.3fV (curr_limit: %0.3f,%0.3f)"%(ip,vol,crange[0],crange[1]))
        
        nt+=1
        if nt>ntry:
            print("max try number reached")
            break
        
    return ip

def custom_measurement(cfgname):
    '''read configuration from file'''

    with open(cfgname) as fl:
        pc=json.load(fl)

    if pc['nprobe'] != nprobe:
        print('incompatible configuration')
        return
    
    pts=[]
    resarr={}

    for p in pc['conf']:
        resarr[tuple(p[0])]=(p[0], None)

    for p in pc['conf']:

        if not msrev.is_set(): 
            print('measurement aborted')
            break;

        pts.append(p[0])

        pm=p[1][0]
        pp=p[1][1]
        vm=p[1][2]
        vp=p[1][3]

        print("probe conf: pm={} pp={} vm={} vp={}".format(pm,pp,vm,vp))
        
        # measure self potential. FIXME! statistics
        print(g.discharge(injection_volt_low,verbose=True))
        sleep(0.5)
        g.probe(0,0,vm,vp)
        sv=g.measure_voltage()
        
        if ntry<max_measurement_try  and sv>=voltage_limit:
            ntry+=1
            print('bad probe contact (V_self).. retrying..')
            continue
            
        # injection
        g.inject(False)
        sleep(0.5)

        g.probe(pm,pp,vm,vp)
        g.set_injection(injection_low_pwm)
        g.inject()
        sleep(0.5)
        
        mi=0.0
        mi=adjustcurrent(crange)
        mv=g.measure_voltage()
        
        if ntry<max_measurement_try and mv>=voltage_limit:
            ntry+=1
            print('bad probe contact.. retrying...')
            continue
        
        if mi!=0.0:
            mr=np.abs((mv-sv)/mi)
        else:
            mr=float('nan')

        resarr[tuple(p[0])]=(p[0], [mv,mi,mr,sv])
        
        if firsttake:
            rrange={'low':mr,'high':mr}
            firsttake=False
        else:
            if rrange['low']>mr:
                rrange['low']=mr
            if rrange['high']<mr:
                rrange['high']=mr
                                
        print("R=%0.2fOhm V=%0.3fmV C_inj=%0.4fmA V_self=%0.3fmV"%(mr,mv,mi,sv))
        ntry=0
    
    g.probe_off()   # turn off relays
    g.discharge(injection_volt_low)
    g.flush()
    msrev.clear()

def measure_resistances():
    global probres
    g.discharge(10.0)
    g.set_injection(injection_low_pwm)
    g.probe(1,2,0,0)

    for p in range(len(probres)):

        if not msrev.is_set():
            break
        
        I=g.measure_current()
        V=g.measure_injection()
        S=g.measure_shunt()
        
        try:
            probres[p]=((V+S)/I,V+S,I)
        except:
            probres[p]=(nan,nan,nan)
        print('I=%0.4f V=%0.4f S=%0.2f'%(I,V,S))
        g.inject(False)
        sleep(0.2)
        g.shift()
        g.inject()
        
    g.probe_off()   
    msrev.clear()

def saveData():
    fl=open(filename_prefix+str(int(dt.timestamp(dt.now()))),'w')
    fl.write('# geoelectric measurement data\n')
    fl.write('# rosandi, 2020\n')
    fl.write('# Geophysics Universitas Padjadjaran\n')
    fl.write('# fields: volt curr res vself conf\n')
    for a in resarr:
        for b in a:
            fl.write(str(b)+'\n')
    fl.close()

def saveRes():
    fl=open(filename_prefix+'res-'+str(int(dt.timestamp(dt.now()))),'w')
    fl.write('# resistance measurement data\n')
    fl.write('# rosandi, 2020\n')
    fl.write('# Geophysics Universitas Padjadjaran\n')
    fl.write('# fields: P1 P2 R V I\n')
    for a in range(len(probres)):
        fl.write(str((a+1,a+2)+probres[a])+'\n')
    fl.close()

    
##########################
###### MAIN PROGRAM ######
##########################

if __name__ == "__main__":
    
    for arg in sys.argv:
        if arg.find('comm=') == 0:
            comm=arg.replace('comm=','')
        if arg.find('speed=') == 0:
            speed=int(arg.replace('speed=',''))

    # don't forget to initialize first
    try:
        g.init(comm,speed)
        print('calibrating...')
        print('calibration parameters: ', g.soft_calibrate(n=5,verbose=True))
    except:
        import gelecdummy as g
        g.init('null')

    g.set_naverage(20)

    if not comm:
        print("arguments required: comm=[comm-port]")
        exit(-1)
    
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

