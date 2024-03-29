#!/usr/bin/env python

import sys
import os
import json

from PyQt5.QtCore import Qt, QRect, QTimer

from PyQt5.QtWidgets import (
        QWidget, QApplication, QScrollArea, 
        QFrame, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout, 
        QPushButton, QDialog, QFileDialog, QLineEdit, QPlainTextEdit,
        QMessageBox
        )

from PyQt5.QtGui import QPainter, QPixmap, QColor, QFont, QBrush, QPen

#from PyQt5.QtGui import QFont, QIntValidator, QDoubleValidator
#from PyQt5.QtCore import Qt, QTimer, QUrl, QDate, QTime, QRect

from threading import Thread

colorcode=["#FFFFFF","#2D979E","#2D9F9F","#2CA09A","#2BA194","#2BA38E",
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


import gectr as gc

for arg in sys.argv:
    if arg.find('config=') == 0:
        fnm=arg.replace('config=','')
        print(f'loading {fnm}...')
        with open(fnm) as fl:
            gc.devcfg=json.load(fl)

css='seismolog.css'
with open(css) as c: css=c.read()

class logWindow(QDialog):
    def __init__(_, master):
        super(logWindow, _).__init__(master)
        _.logtext=QPlainTextEdit()
        _.logtext.setReadOnly(True)
        _.logtext.setPlainText(gc.logstring)
        cbtn=QPushButton('&Close')
        cbtn.clicked.connect(lambda: _.close())
        lyo=QVBoxLayout()
        lyo.addWidget(_.logtext)
        lyo.addWidget(cbtn)
        _.setLayout(lyo)
        _.exec_()

class logBox(QWidget):
    def __init__(_,master):
        super(logBox,_).__init__(master)
        fn=QFont()
        fn.setPointSize(8)
        _.logtext=QPlainTextEdit(_)
        _.logtext.setReadOnly(True)
        _.logtext.setFont(fn)
        lyo=QVBoxLayout()
        lyo.addWidget(_.logtext)
        _.setGeometry(QRect(600, 400, 400, 120))
        _.setLayout(lyo)
        _.hide()

    def setText(_,txt):
        _.logtext.setPlainText(txt)
        mm=_.logtext.verticalScrollBar().maximum()
        _.logtext.verticalScrollBar().setValue(mm);

    def clear(_):
        _.logtext.clear()

class setDialog(QDialog):
    def __init__(_,master):
        super(setDialog,_).__init__(master)
        _.create()
        _.exec_()

    def applysettings(_):
        try:
            newcfg = {
                    'crange': (float(_.ecrangemin.text()), float(_.ecrangemax.text())),
                    'injection_low_pwm': int(_.einlow.text()),
                    'injection_pwm_increment': int(_.eininc.text()),
                    'injection_volt_limit': float(_.einvhi.text()),
                    'injection_volt_low': float(_.einvlo.text()),
                    'injection_max_try': int(_.eintry.text()),
                    'voltage_limit': float(_.evlim.text()),
                    'max_measurement_try': int(_.emtry.text()),
                    'filename_prefix': _.eprefix.text()
                    }

            gc.devcfg=newcfg
        
        except Exception as e:
            print(e)
            return False

        return True

    def savesettings(_):
        if _.applysettings():
            fnm=QFileDialog.getSaveFileName(_, 'Save Configuration', filter='*.json')
            fnm=fnm[0]
            if fnm:
                with open(fnm,'w') as fl:
                    json.dump(gc.devcfg,fl)
                _.close()

    def applyandclose(_):
        if _.applysettings():
            _.close()

    def create(_):
        _.setWindowTitle("GE Settings")
        _.ecrangemin=QLineEdit(f"{gc.devcfg['crange'][0]}")
        _.ecrangemax=QLineEdit(f"{gc.devcfg['crange'][1]}")
        _.einlow=QLineEdit(f"{gc.devcfg['injection_low_pwm']}")
        _.eininc=QLineEdit(f"{gc.devcfg['injection_pwm_increment']}")
        _.einvhi=QLineEdit(f"{gc.devcfg['injection_volt_limit']}")
        _.einvlo=QLineEdit(f"{gc.devcfg['injection_volt_low']}")
        _.eintry=QLineEdit(f"{gc.devcfg['injection_max_try']}")
        _.evlim=QLineEdit(f"{gc.devcfg['voltage_limit']}")
        _.emtry=QLineEdit(f"{gc.devcfg['max_measurement_try']}")
        _.eprefix=QLineEdit(f"{gc.devcfg['filename_prefix']}")

        logbtn=QPushButton('&Log')
        cancelbtn=QPushButton("&Cancel")
        applybtn=QPushButton("&Apply")
        savebtn=QPushButton("&Save")

        logbtn.clicked.connect(lambda: logWindow(_))
        cancelbtn.clicked.connect(lambda: _.close())
        applybtn.clicked.connect(lambda: _.applyandclose)
        savebtn.clicked.connect(_.savesettings)

        frm=QFormLayout()
        frm.addRow("low current limit", _.ecrangemin)
        frm.addRow("high current limit", _.ecrangemax)
        frm.addRow("low injection pwm", _.einlow)
        frm.addRow("pwm increment", _.eininc)
        frm.addRow("inject volt high limit", _.einvhi)
        frm.addRow("inject volt low limit", _.einvlo)
        frm.addRow("injection try count", _.eintry)
        frm.addRow("measurement volt limit", _.evlim)
        frm.addRow("max measure try", _.emtry)
        frm.addRow("filename prefix", _.eprefix)

        btn=QHBoxLayout()
        btn.addWidget(cancelbtn)
        btn.addWidget(applybtn)
        btn.addWidget(savebtn)
        btn.addWidget(logbtn)

        grid=QGridLayout()
        grid.addLayout(frm,0,0)
        grid.addLayout(btn,1,0)
        _.setLayout(grid)


class cmdButton(QPushButton):
    def __init__(_,txt, act=None, sty='cmdButton'):
        super(cmdButton,_).__init__(txt)
        _.setObjectName(sty)

        if(act):
            _.clicked.connect(act)

class Plotter(QFrame):
    def __init__(_, master):
        super(Plotter, _).__init__()
        _.master=master
        _.resize(1024,600)
        _.scrimg=QPixmap(1024, 600)
        _.xof=50
        _.yof=100
        _.xskip=40
        _.yskip=30
        _.dia=20
        _.cbx=20
        _.cby=30
        _.datumbox={}
        _.probepos={}
        _.mapped=False

    def colorscale(_,painter):
        x=_.cbx+30
        y=_.cby

        for c in range(1,len(colorcode)):
            painter.setPen(QPen(QColor(colorcode[c]), 1, Qt.SolidLine))
            painter.setBrush(QBrush(QColor(colorcode[c]), Qt.SolidPattern))
            painter.drawRect(x,y,3,10)
            x+=3

        painter.setFont(QFont('Arial', 8))
        painter.setPen(Qt.magenta)
        painter.drawText(_.cbx,_.cby+10, "%0.2f"%gc.rmin)
        painter.drawText(x+10,_.cby+10, "%0.2f"%gc.rmax)

    def drawpoints(_):

        cfg=_.master.pconf

        x=_.xof+10
        y=_.yof+10
        d=_.dia
        xs=_.xskip
        ys=_.yskip
        np=cfg['nprobe']
        pos=cfg['conf']

        wpix=np*xs+2*_.xof+40
        wpiy=np*ys+2*_.xof+40

        img=QPixmap(wpix,wpiy)
        p=QPainter(img)
        p.eraseRect(QRect(0,0,wpix,wpiy))

        pp={}
        p.setPen(QPen(Qt.black, 2, Qt.SolidLine))
        p.setBrush(QBrush(Qt.white,Qt.SolidPattern))

        for ip in pos:
            pp[tuple(ip[0])]=None

        for i in range(np):
            p.drawEllipse(x,y,d,d)
            _.probepos[i+1]=(x,y)   # count from 1
            x+=xs

        x=_.xof+10
        y+=ys
        off=cfg['roffs']

        xmax=0
        ymax=0

        for j in range(1,np+1):
            x=_.xof+10
            for i in range(1,np+1): # x-major
                oo=0
                if(j<len(off)):
                    oo=int(off[j-1]*xs)
                    #print(oo,off[j],xs)

                if (i,j) in pp:
                    px=x+oo
                    py=y
                    
                    p.drawRect(px,py,d,d)
                    pp[i,j]=[px,py,QColor(Qt.darkGray)]

                    x+=xs
                    if xmax<x: xmax=x
                    if ymax<y: ymax=y

            y+=ys
        
        _.colorscale(p)
        p.end()

        _.datumbox=pp
        _.mapped=True
        
        return img

    def updatepoints(_):
        p=QPainter(_.scrimg)
        p.setPen(QPen(Qt.black, 2, Qt.SolidLine))
        d=_.dia
        db=_.datumbox

        p.eraseRect(QRect(0,0,_.scrimg.width(),_.scrimg.height())) 
        p.setPen(QPen(Qt.black, 2, Qt.SolidLine))
        p.setBrush(QBrush(Qt.white,Qt.SolidPattern))

        for i in range(1,_.master.pconf['nprobe']+1):
            p.drawEllipse(_.probepos[i][0],_.probepos[i][1],d,d)

        if gc.pm>0:
            prb=_.probepos
            p.setBrush(QBrush(Qt.black,Qt.SolidPattern))
            p.drawEllipse(prb[gc.pm][0],prb[gc.pm][1],d,d)
            p.setBrush(QBrush(Qt.red,Qt.SolidPattern))
            p.drawEllipse(prb[gc.pp][0],prb[gc.pp][1],d,d)
            p.setBrush(QBrush(Qt.blue,Qt.SolidPattern))
            p.drawEllipse(prb[gc.vm][0],prb[gc.vm][1],d,d)
            p.setBrush(QBrush(Qt.green,Qt.SolidPattern))
            p.drawEllipse(prb[gc.vp][0],prb[gc.vp][1],d,d)

        # FIXME
        for rr in gc.resarr:
            if rr in db:
                cid=gc.resmap(rr, colorcode)
                db[rr][2]=QColor(colorcode[cid])

        for g in db:
            p.setBrush(QBrush(db[g][2], Qt.SolidPattern))
            p.drawRect(db[g][0], db[g][1], d,d)

        p.setFont(QFont('Arial', 8))
        p.setPen(Qt.magenta)
        
        for g in range(1,_.master.pconf['nprobe']):
            if gc.probres[g,g+1]:
                p.drawText(_.probepos[g][0]+15, _.probepos[g][1]-5, '%0.2f'%gc.probres[g,g+1][0])

        _.colorscale(p)
        p.end()
    
    def paintEvent(_, event):
        pc=QPainter(_)

        if _.master.pconf:
            if _.mapped:
                _.updatepoints()
            else:
                _.scrimg=_.drawpoints()
                _.resize(_.scrimg.width(), _.scrimg.height())
            
            pc.drawPixmap(0,0,_.scrimg)
        else:
            pc.setPen(Qt.yellow)
            pc.setFont(QFont('Arial', 20))
            pc.drawText(100, 200, "no probe configuration loaded")

class Controls(QFrame):
    def __init__(_, master):
        super(Controls, _).__init__()
        _.master=master
        _.createControls()

    def createControls(_):
        _.master.cfg=cmdButton('Probe Conf', _.master.probeconf)
        _.master.acq=cmdButton('Acquire', _.master.doacq)
        _.master.res=cmdButton('Resistance', _.master.dores)
        _.master.sett=cmdButton('Settings', _.master.doset, sty='cfgButton')

        lyo=QHBoxLayout()
        lyo.addWidget(_.master.cfg)
        lyo.addWidget(_.master.acq)
        lyo.addWidget(_.master.res)

        slo=QVBoxLayout()
        slo.addWidget(_.master.sett)
        slo.addWidget(cmdButton('Quit', lambda: _.master.close(), sty='cfgButton'))

        mlo=QHBoxLayout()
        mlo.addLayout(lyo,5)
        mlo.addLayout(slo,1)
        
        _.setLayout(mlo)

class GEWin(QWidget):
    def __init__(_,w,h):
        super(GEWin, _).__init__()
        _.resize(w,h)
        _.setWindowTitle("GeoElectric Acquisition")
        _.pconf=None
        _.canvas=Plotter(_)
        _.resarr=None
        _.proarr=None
        _.uptimer=QTimer()
        _.uptimer.timeout.connect(_.update)
        _.createGadgets()
        _.logwin=logBox(_)
        _.show()

    def createGadgets(_):
        scroll=QScrollArea()
        scroll.setAlignment(Qt.AlignCenter)
        scroll.setWidget(_.canvas)
        lyo=QVBoxLayout()
        lyo.addWidget(scroll,5)
        lyo.addWidget(Controls(_),1)
        _.setLayout(lyo)

    def grayButton(_,doit):
        doit=not doit
        _.acq.setEnabled(doit)
        _.res.setEnabled(doit)
        _.sett.setEnabled(doit)

    def update(_):
        _.canvas.repaint()
        _.logwin.setText(gc.logstring)
        
        if not gc.msrev.is_set():
            _.uptimer.stop()
            _.cfg.setText('Probe Conf')
            _.grayButton(False)
            _.logwin.hide()

    def probeconf(_): # this button has 2 functions..: cancel
        if gc.msrev.is_set():
            gc.msrev.clear()
            #_.cfg.setText('Probe Conf')
            #_.grayButton(False)

        else:
            fnm=QFileDialog.getOpenFileName(_, 'Open probe configuration', filter='*.json')
            fnm=fnm[0]
            if fnm =='': return

            with open(fnm) as fl:
                pc=json.load(fl)
            
            if 'device_configuration' in pc:
                confirm=QMessageBox.question(_, 'Device Configuration', 
                        'Device configuration found.\nLoad as new configuration ?', 
                        QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                if confirm==QMessageBox.No:
                    pc['device_configuration']={}

            _.pconf=pc
            gc.set_conf(_.pconf)
            _.canvas.repaint()

    def doacq(_):
        if(_.pconf==None): 
            _.probeconf()
        
        _.cfg.setText('&CANCEL')
        _.grayButton(True)

        gc.msrev.set()
        _.logwin.show()  # FIXME
        _.logwin.clear()

        trid=Thread(target=gc.custom_measurement)
        trid.start()
        _.uptimer.start(100)


    def dores(_):
        if(_.pconf==None): 
            _.probeconf()

        _.cfg.setText('&CANCEL')
        _.grayButton(True)
        gc.msrev.set()

        _.logwin.show()  # FIXME
        _.logwin.clear()

        trid=Thread(target=gc.measure_resistances)
        trid.start()

        _.uptimer.start(100)

    def doset(_):
        setDialog(_)

    def closeEvent(_,ev):
        confirm=QMessageBox.question(_, 'Quit', 'Confirm to quit?', 
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if confirm == QMessageBox.Yes:
            gc.msrev.clear()
            _.close()
            ev.accept()
        else:
            ev.ignore()


class GEApps(QApplication):
    def __init__(_):

        gc.init_dev('/dev/ttyUSB0', 9600)
        super(GEApps, _).__init__(sys.argv)
        _.setApplicationName('GEController')
        _.guiwin=GEWin(1024,600)
        _.setStyleSheet(css)

GEApps().exec_()

