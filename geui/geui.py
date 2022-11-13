#!/usr/bin/env python

import sys
import os
import json

from PyQt5.QtCore import Qt, QRect

from PyQt5.QtWidgets import (
        QWidget, QApplication, QScrollArea, 
        QFrame, QVBoxLayout, QHBoxLayout, QPushButton,
        QFileDialog
        )

from PyQt5.QtGui import QPainter, QPixmap, QColor, QFont, QBrush, QPen

#from PyQt5.QtGui import QFont, QIntValidator, QDoubleValidator
#from PyQt5.QtCore import Qt, QTimer, QUrl, QDate, QTime, QRect

css='seismolog.css'
with open(css) as c: css=c.read()

class cmdButton(QPushButton):
    def __init__(_,txt, act=None):
        super(cmdButton,_).__init__(txt)
        _.setObjectName('cmdButton')

        if(act):
            _.clicked.connect(act)

class Plotter(QFrame):
    def __init__(_, master):
        super(Plotter, _).__init__()
        _.master=master
        _.resize(1024,600)
        _.scrimg=QPixmap(1024, 600)
        _.xof=50
        _.yof=50
        _.xskip=40
        _.yskip=30
        _.dia=20

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

        pp=[]
        p.setPen(QPen(Qt.black, 2, Qt.SolidLine))
        p.setBrush(QBrush(Qt.darkGray,Qt.SolidPattern))

        for ip in pos:
            pp.append(tuple(ip[0]))

        for i in range(np):
            p.drawEllipse(x,y,d,d)
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
                    p.drawRect(x+oo,y,d,d)
                    x+=xs
                    if xmax<x: xmax=x
                    if ymax<y: ymax=y

            y+=ys

        p.end()
        return img
        
    
    def paintEvent(_, event):
        pc=QPainter(_)

        if _.master.pconf:
            _.scrimg=_.drawpoints()
            pc.drawPixmap(0,0,_.scrimg)
        else:
            pc.setPen(QColor(Qt.yellow))
            pc.setFont(QFont('Arial', 20))
            pc.drawText(100, 200, "no probe configuration loaded")


class Controls(QFrame):
    def __init__(_, master):
        super(Controls, _).__init__()
        _.master=master
        _.createControls()

    def createControls(_):
        cfg=cmdButton('Probes Conf', _.master.probeconf)
        acq=cmdButton('Acquire', _.master.doacq)
        res=cmdButton('Resistance', _.master.dores)
        sett=cmdButton('Settings', _.master.doset)

        lyo=QHBoxLayout()
        lyo.addWidget(cfg)
        lyo.addWidget(acq)
        lyo.addWidget(res)
        lyo.addWidget(sett)
        _.setLayout(lyo)

class GEWin(QWidget):
    def __init__(_,w,h):
        super(GEWin, _).__init__()
        _.resize(w,h)
        _.setWindowTitle("GeoElectric Acquisition")
        _.pconf=None
        _.canvas=Plotter(_)
        _.createGadgets()
        _.show()

    def createGadgets(_):
        scroll=QScrollArea()
        scroll.setWidget(_.canvas)
        lyo=QVBoxLayout()
        lyo.addWidget(scroll,5)
        lyo.addWidget(Controls(_),1)
        _.setLayout(lyo)

    def probeconf(_):
        fnm=QFileDialog.getOpenFileName(_, 'Open probe configuration', filter='*.json')
        fnm=fnm[0]
        if fnm =='': return

        with open(fnm) as fl:
            pc=json.load(fl)

        _.pconf=pc
        _.canvas.repaint()


    def doacq(_):
        print('do acquisition')

    def dores(_):
        print('resistance measurement')

    def doset(_):
        print('acquisition settings')


class GEApps(QApplication):
    def __init__(_):
        super(GEApps, _).__init__(sys.argv)
        _.setApplicationName('GEController')
        _.guiwin=GEWin(1024,600)
        _.setStyleSheet(css)

GEApps().exec_()

