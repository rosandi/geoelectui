#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#---------------------------------------------------------
# Program to operate Geoelectric Prototype 
# PrototypeInstrument Code: Geothings IGF-02 Geoelectric
#
#  (c) Rosandi, 2020
#---------------------------------------------------------

from time import sleep
import sys

NPROBE=16
READY=False
current_offset=0.0

def flush():
	return "ok"

def send(scmd):
	return scmd+' ok'

def inject(stat=True):
	return 'inject'

def discharge(minvolt, minpwm=5, verbose=False):
	return 'discharge'
	
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
	return 0,0,0,0
	
def shift():
	send('s 0 1')

def incr_injection(n=1):
	send('i'*n)

def decr_injection(n=1):
	send('d'*n)

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

def calibrate():
	send('C')
	
def soft_calibrate(n=5, verbose=False):
	return "soft calibration"

def measure_voltage():
	return 1

def measure_current():
	return 1
	
def measure_injection():
	return 1
	
def measure_shunt():
	return 1
	
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
			print(vv[0]/avg,vv[1]/avg,vv[2]/avg,vv[3]/avg)
				
	except:
		pass
	
def display():
	send('e 0 0 %clear')
	send('e 0 0 Resistivity Meter')
	send('e 0 1 GeoPhy Instrument')
	send('e 0 2 Univ. Padjadjaran ')

def init(sdev,speed=9600):
	print("!! DUMMY gelec interface library !!")
	
	return 'ok'
