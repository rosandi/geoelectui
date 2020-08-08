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
from tkinter import *
import numpy as np
import sys
from threading import Thread, Event
import gelec as g

WINW=800
WINH=600
WOFFS=0
HOFFS=0
CVSH=350

colorcode=["#2E909D","#2D979E","#2D9F9F","#2CA09A","#2BA194","#2BA38E",
           "#2AA488","#29A582","#29A67B","#28A775","#27A96E","#27AA67",
           "#26AB60","#26AC58","#25AD50","#24AF48","#23B040","#23B138",
           "#22B22F","#21B426","#24B521","#2CB620","#34B71F","#3CB91F",
           "#45BA1E","#4EBB1D","#56BC1C","#60BE1C","#69BF1B","#73C01A",
           "#7DC11A","#87C319","#91C418","#9BC718","#A5CB18","#B0CE18",
           "#BBD118","#C5D418","#D1D719","#DAD819","#DDD219","#E0CD1A",
           "#E3C61D","#E5C020","#E8B922","#EBB225","#EDAB28","#F0A42B",
           "#F29D2E","#F49531","#F78D34","#F98637","#FB7E39","#FD763C",
           "#FF6E3F","#FF6642","#FF5E45","#FF5548","#FF4D4B","#FF4E4E",
           "#FF5050","#FF5353","#FF5656","#FF5959","#FF5C5C"]

# ----------- VARIABLES -----------

maxlayer=3
msrthread_id=None
msrev=Event()

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

##### COMMAND LINE PARAMETERS ####
#
# macOS: /dev/cu.wchusbserial1420
# Linux: /dev/ttyUSB0 or /dev/ttyACM0

comm='/dev/ttyUSB0'
speed=9600

for arg in sys.argv:
    if arg.find('comm=') == 0:
        comm=arg.replace('comm=','')
    if arg.find('speed=') == 0:
        speed=int(arg.replace('speed=',''))
    if arg.find('size=') == 0:
        WINW=int(arg.replace('size=','').split('x')[0])
        WINH=int(arg.replace('size=','').split('x')[1])
    if arg.find('offset=') == 0:
        WOFFS=int(arg.replace('offset=','').replace('+',' ').split()[0])
        HOFFS=int(arg.replace('offset=','').replace('+',' ').split()[1])

boxarr=[] # box figure array (color, values, etc)
proarr=[] # probe position (surface)
resarr=[] # measured resistivity array
probres=[] # interprobe resistances
conarr=[] # probe configuration

# dP+1==prob distance
# dP=0 pMax=3, dp=1 pMax=6, 9, 12
# pmax=(dP+1)*3
# max dP: pmax<16

def calcpoints():
	global resarr,boxarr,conarr, probres
		
	probres=(g.NPROBE-1)*[(-1,-1,-1)]
	dPmax=0
	
	while True:
		if ((dPmax+1)*3) > g.NPROBE:
			break
		dPmax+=1
		
	nbox=g.NPROBE-3
	
	for dP in range(dPmax):
		
		if (dP>maxlayer):
			break
			
		pm=1
		pp=(dP+1)*3+1
		vm=pm+dP+1
		vp=vm+dP+1
		
		conarr.append({'conf': (pm,pp,vm,vp), 'nbox': nbox})
		resarr.append(nbox*[(-1,-1,-1,-1, (0,0,0,0))])
		nbox-=3
	
#for ar in boxarr:
#	print(ar)

#for ar in resarr:
#	print(ar)

#for ar in conarr:
#	print(ar)

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

def automated_measurement():
	global resarr,boxarr,rrange
	
	firsttake=True
	
	for prow in range(len(resarr)):
		
		pconf=conarr[prow]['conf']
		aa=pconf[0]
		bb=pconf[1]
		cc=pconf[2]
		dd=pconf[3]
		v=0
		ntry=0
		
		while v < len(resarr[prow]):
#		for v in range(len(resarr[prow])):

			if not msrev.is_set():
				break

			print("probe conf: pm={} pp={} vm={} vp={}".format(aa,bb,cc,dd))
			
			# measure self potential. FIXME! statistics
			g.discharge(injection_volt_low,verbose=True)
			
			g.probe(0,0,cc,dd)
			sv=g.measure_voltage()
			
			if ntry<max_measurement_try  and sv>=voltage_limit:
				ntry+=1
				print('bad probe contact (V_self).. retrying..')
				continue
				
			# injection
			g.probe(aa,bb,cc,dd)
			g.set_injection(injection_low_pwm)
			g.inject()			
			mi=0.0
#			mi=adjustcurrent(crange,ntry=10)
			mi=adjustcurrent(crange)

			mv=g.measure_voltage()
			
			if ntry<max_measurement_try and mv>=voltage_limit:
				ntry+=1
				print('bad probe contact.. retrying...')
				continue
			
			mr=-1
			
			if mi!=0.0:
				mr=np.abs((mv-sv)/mi)
				resarr[prow][v]=(mv,mi,mr,sv,(aa,bb,cc,dd))
			
			if firsttake:
				rrange={'low':mr,'high':mr}
				firsttake=False
			else:
				if rrange['low']>mr:
					rrange['low']=mr
				if rrange['high']<mr:
					rrange['high']=mr
									
			print("R=%0.2fOhm V=%0.3fmV C_inj=%0.4fmA V_self=%0.3fmV"%(mr,mv,mi,sv))
			aa+=1
			bb+=1
			cc+=1
			dd+=1
			v+=1
			ntry=0
		
		if not msrev.is_set():
			print("measurement aborted")
			break
		
	g.probe_off()	# turn off relays
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
			probres[p]=(-1,-1,-1)
		g.shift()
		
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

	
########################
#### INTERFACE CODE ####
########################

boxofs=50
boxski=100
boxsz=40
boxsep=5

mw=Tk()
mw.title("GeoPhy Resistivity Meter")
mw.geometry("{}x{}+{}+{}".format(WINW,WINH,WOFFS,HOFFS))
DrawArea=Frame(mw)
CommandArea=Frame(mw)
ParamArea=Frame(mw)
DrawArea.grid(row=0,column=0,columnspan=2)
CommandArea.grid(row=1,column=0,pady=10)
ParamArea.grid(row=1,column=1,pady=10)

cvs=Canvas(DrawArea,width=WINW,height=CVSH,bg='white')
cvs.pack()

dosave=IntVar()
dorep=IntVar()
dosave.set(1)
dorep.set(0)
ckeylow=None
ckeyhigh=None

def drawresmap():
	global boxarr,proarr,ckeylow,ckeyhigh

	bx=boxofs
	by=boxski-35
	prad=20

	maxcol=g.NPROBE

	# probe positions
	for i in range(maxcol):
		p=cvs.create_oval(bx,by,bx+prad,by+prad,fill='yellow')
		r=cvs.create_text(bx+2*prad,by-prad,text='--',state=HIDDEN)
		bx+=boxsz+boxsep
		proarr.append({'id': p, 'color': 'yellow', 'resid':r})

	bxx=boxofs+3*boxsz/2-boxsep/2
	by=boxski
	
	for p in conarr:
		bx=bxx
		tarr=[]

		for i in range(p['nbox']):
			b=cvs.create_rectangle(bx,by,bx+boxsz,by+boxsz,fill='gray')
			tarr.append({'id': b,'color': 'gray'})
			bx+=boxsz+boxsep

		boxarr.append(tarr)
		by+=boxsz+boxsep
		bxx+=3*boxsz/2 + boxsep
		
	
	cbx=100
	cby=CVSH-30
	
	for c in colorcode:
		cvs.create_rectangle(cbx,cby,cbx+5,cby+20,outline=c,fill=c)
		cbx+=5

	ckeylow=cvs.create_text(75,cby+10,text='%0.2f'%(rrange['low']),fill=colorcode[0])
	ckeyhigh=cvs.create_text(460,cby+10,text='%0.2f'%(rrange['high']),fill=colorcode[64])
	
def enableWidget(wlist, en=True): # wlist<-widget list
	if en:
		for a in wlist:
			a['state']=NORMAL
	else:
		for a in wlist:
			a['state']=DISABLED

def update_display():
	for i in range(len(resarr)):
		for j in range(len(resarr[i])):
			r=resarr[i][j][2]
			if r==-1:
				continue
				
			if rrange['low'] >= rrange['high']:
				c=32
			else:
				c=int(len(colorcode)*(r-rrange['low'])/(rrange['high']-rrange['low']))
				
			if c>64:
				c=64
				
			boxarr[i][j]['color']=colorcode[c]

	for b in boxarr:
		for v in b:
			cvs.itemconfig(v['id'],fill=v['color'])
	
	cvs.itemconfig(ckeylow,text='%0.2f'%(rrange['low']))
	cvs.itemconfig(ckeyhigh,text='%0.2f'%(rrange['high']))
	
	cvs.update_idletasks()

	if msrev.is_set():
		mw.after(100,update_display)
	else:
		bmsr['text']='MEASURE'
		enableWidget(entries+buttons)
		if dosave.get():
			saveData()
			if dorep.get():
				measurebtn()	

def update_resval():
	for p in range(len(probres)):
		if probres[p][0]>0:
			cvs.itemconfig(proarr[p]['resid'],state=NORMAL,text='%0.0f'%(probres[p][0]))
	
	if msrev.is_set():
		mw.after(100,update_resval)
	else:
		rmsr['text']='RESISTANCE'
		enableWidget(entries+[bmsr,brun,bcali])
		if dosave.get():
			saveRes()

##### COMMANDS #####

# measurement button functions

def measurebtn():
	global msrthread_id, resarr
	
	if msrev.is_set():
		print("request to abort...")
		bmsr['text']='MEASURE'
		dorep.set(0)
		msrev.clear()
		enableWidget(entries+buttons)
		
	else:
		enableWidget(entries+buttons,False)
		apply_param()
		bmsr['text']='STOP MEASUREMENT'
		for b in boxarr:
			for v in b:
				v['color']='gray'
				cvs.itemconfig(v['id'],fill=v['color'])

		cvs.update_idletasks()

		for i in range(len(resarr)):
			for j in range(len(resarr[i])):
				resarr[i][j]=(-1,-1,-1,-1)
				
		msrev.set()
		msrthread_id=Thread(target=automated_measurement)
		msrthread_id.start()
		update_display()

def runcheck():
	g.send('R')

def runcali():
	cal=g.soft_calibrate(5)
	print(cal)

def resbtn():
	global msrthread_id,probres
	if msrev.is_set():
		print("request to abort (res)...")
		rmsr['text']='RESISTANCE'
		msrev.clear()
		enableWidget(entries+[bmsr,brun,bcali])
	else:
		enableWidget(entries+[bmsr,brun,bcali],False)	
		rmsr['text']='CANCEL MEASUREMENT'	
		msrev.set()
		msrthread_id=Thread(target=measure_resistances)
		msrthread_id.start()
		update_resval()

cmd_pos=0

def commandButton(label, cmd):
	global cmd_pos
	bt=Button(CommandArea, text=label, command=cmd)
	bt.grid(row=cmd_pos,column=0,sticky='WE')
	cmd_pos+=1
	return bt
	
# the buttons

bmsr=commandButton('MEASURE',measurebtn)
rmsr=commandButton('RESISTANCE',resbtn)
brun=commandButton('CHECK RELAY',runcheck)
bcali=commandButton('CALIBRATE',runcali)

fck=Frame(CommandArea)
fck.grid(row=cmd_pos,pady=10)
Checkbutton(fck, text='Save Measurement Data',variable=dosave).grid(row=0,sticky='W')
Checkbutton(fck, text='Loop Measurement',variable=dorep).grid(row=1,sticky='W')

buttons=[brun,bcali]

#### PARAMS ####

entries=[]
entrie_pos=0

def paramEntry(label,text,unit):
	global entrie_pos
	Label(ParamArea,text=label).grid(row=entrie_pos,column=0,sticky='W')
	ent=Entry(ParamArea)
	ent.insert(END,text)
	ent.grid(row=entrie_pos,column=1)
	if unit != '':
		Label(ParamArea,text=unit).grid(row=entrie_pos,column=2,sticky='W')
	entries.append(ent)
	entrie_pos+=1
	return ent

def apply_param():
	global crange, injection_pwm_increment, injection_volt_low
	global voltage_limit
	
	c0=float(entry_min_current.get())
	c1=float(entry_max_current.get())
	crange=(c0,c1)
	
	voltage_limit=float(entry_max_volt.get())
	injection_pwm_increment=int(entry_pwm_incr.get())
	injection_volt_low=float(entry_discharge_volt.get())
	injection_max_try=int(entry_imaxtry.get())
	max_measurement_try=int(entry_mmaxtry.get())
	filename_prefix=entry_filename.get()

# the entries
entry_min_current=paramEntry('Current Low Limit ', "%0.3f"%(crange[0]),' mA')
entry_max_current=paramEntry('Current High Limit ', "%0.3f"%(crange[1]),' mA')
entry_max_volt=paramEntry('Voltage Limit ', '%0.2f'%(voltage_limit),' mV')
entry_discharge_volt=paramEntry('Discharge Voltage ', '%0.3f'%(injection_volt_low),' V')
entry_pwm_incr=paramEntry('PWM Increment ', str(injection_pwm_increment),'')
entry_imaxtry=paramEntry('Max Injection Try ', str(injection_max_try),'')
entry_mmaxtry=paramEntry('Max Measurement Try ', str(max_measurement_try),'')
entry_filename=paramEntry('File Prefix ', filename_prefix,'')

ebt=Button(ParamArea, text='APPLY PARAMETERS', command=apply_param)
ebt.grid(row=entrie_pos,column=0,columnspan=2,pady=10)
entries.append(ebt)

##########################
###### MAIN PROGRAM ######
##########################

# don't forget to initialize first
try:
	g.init(comm,speed)
	print('calibrating...')
	print('calibration parameters: ', g.soft_calibrate(verbose=True))
except:
	import gelecdummy as g
	g.init('null')

g.set_naverage(20)
calcpoints()
drawresmap()

mw.mainloop()
