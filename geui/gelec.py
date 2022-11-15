#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#---------------------------------------------------------
# Program to operate Geoelectric Prototype 
# PrototypeInstrument Code: Geothings IGF-02 Geoelectric
#
#  (c) Rosandi, 2020
#---------------------------------------------------------

from time import sleep
import serial
import sys

ser=None
NPROBE=16
READY=False
WAIT=0.5
WAIT2=2

current_offset=0.0

def plog(s):
    print(s)

def flush():
    s=ser.readlines()
    rs=''
    for ss in s:
        rs=rs+ss.decode().replace('\r','')
    
    while ser.in_waiting:
        ser.read()

    return rs

def send(scmd):
    ser.write(bytes(scmd+' ','ascii'))
    return flush()
    
# pp: plus injection probe
# pm: minus injection probe
# vp: plus voltage probe
# vm: minus voltage probe
# may be zero -> none is active

def probe(pm,pp,vm,vp):

    if (pm or pp) and (pp==pm):
        raise
        
    spp=['-']*NPROBE
    spm=['-']*NPROBE
    svp=['-']*NPROBE
    svm=['-']*NPROBE
    
    if pp:
        spp[NPROBE-pp]='X'
    if pm:
        spm[NPROBE-pm]='X'
    if vp:  
        svp[NPROBE-vp]='X'
    if vm:
        svm[NPROBE-vm]='X'
        
    svm=''.join(svm)
    svp=''.join(svp)
    spm=''.join(spm)
    spp=''.join(spp)
    ss='p'+svp+svm+spp+spm  
    send('q')
    sleep(0.5)
    send(ss)
    
def measure():
    sm=send('m').split()
    vs=send('S')  # shunt voltage
    V=float(sm[0])
    I=float(sm[1])
    J=float(sm[2])
    S=float(vs)
    return V,I,J,S

def shift():
    send('s 0 1')

def incr_injection(n=1):
    return int(send('i'*n).split()[1])

def decr_injection(n=1):
    return int(send('d'*n).split()[1])

def set_injection(ival):
    send('v'+str(ival))

def set_naverage(navg):
    if navg<1:
        navg=1
    if navg>50:
        navg=50
    send('n'+str(navg))

def probe_off():
    send('q')

def inject(stat=True):
    if stat:
        send('Z')
    else:
        send('D')

def discharge(minvolt, minpwm=5, ntry=30, verbose=False):
    set_injection(minpwm)
    send('D')
    vlow=measure_injection()
    tt=0
    while vlow > minvolt:
        vlow=measure_injection()
        if verbose:
            plog("discharging: %0.3fV"%(vlow))
        sleep(1)

        if tt>ntry:
            plog(f"not reaching min volt after {tt} tries")
            plot(f"stop at {vlow} volt")
            break
    
    return ("discharged: %0.3fV"%(vlow))

# just in case there are more than one field take the first!
def measure_voltage():
    return float(send('V').split()[0])

def measure_current():
    return float(send('A').split()[0])

def measure_injection():
    return float(send('J').split()[0])

def measure_shunt():
    return float(send('S').split()[0])

def calibrate():
    a=send('C').split()
    # current_offset shunt_offset
    return float(a[0]),float(a[1])

def soft_calibrate(n=10, verbose=False):
    inject()
    probe_off()
    cu=0.0
    sh=0.0
    for i in range(n):
        a=measure_current()
        b=measure_shunt()
        cu+=a
        sh+=b
        if verbose:
            plog(a,b)
    cu=cu/n
    sh=sh/n
    send("c %0.4f %0.4f 0"%(cu,sh))
    discharge(10.0)
    
    return cu,sh
    
def measure_resistance():
    try:
        return 1000.0*measure_injection()/measure_current()
    except:
        return -1.0

def measure_r():
    a=[]
    probe(1,2,1,1)

    # statistics!
    for i in range(NPROBE-2):
        a.append(measure_resistance())
        shift()
        
    send('q')
    return a

def measureloop(pm,pp,vm,vp,avg=20,rep=0):
    probe(pm,pp,vm,vp)
    try:
        n=0
        while True:
        
            n+=1
            if rep!=0 and n>rep:
                break

            vv=[0,0,0,0]
            for i in range(avg):
                v=measure()
                vv[0]+=v[0]
                vv[1]+=v[1]
                vv[2]+=v[2]
                vv[3]+=v[3]
            plog(f'{vv[0]/avg}, {vv[1]/avg}, {vv[2]/avg}, {vv[3]/avg}')
                
    except:
        pass
    
def display():
    send('e 0 0 %clear')
    send('e 0 0 Resistivity Meter')
    send('e 0 1 GeoPhy Instrument')
    send('e 0 2 Univ. Padjadjaran ')

def close():
    flush()

def init(sdev,speed=9600):
    global ser
    try:
        ser=serial.Serial(sdev, speed, timeout=1)
        sleep(2) # just wait a bit
        # display()
        READY=True
    except:
        plog(f'CAN NOT OPEN DEVICE! {sdev}')
        
    return flush()
