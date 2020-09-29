# -*- coding: utf-8 -*-
"""
Created on Fri Apr 03 15:15:55 2020

@author: nguyen
"""

import sys, time
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QMenu, QAction
from PyQt5.QtCore import Qt

import pyqtgraph as pg

import ui_brooks_simple as ihm
import qdarkstyle

from serial.tools.list_ports import comports
import numpy as np

from brooks_custom import BrooksCustom as BrooksMFC
from doomy import Doomy as DoomyMFC

import re

MAX_INSTANCE_NUMBER = 10

class MainWindow(QMainWindow, ihm.Ui_MainWindow):
    """
    Dessine l'interface graphique
    """    
    def __init__(self, nb_mfcs=1, simulation_mode=True):
        super(MainWindow, self).__init__()
        self.simulation_mode = simulation_mode
        self.period_timer = 200 #ms
        self.mon_timer = None
        assert nb_mfcs <= MAX_INSTANCE_NUMBER
        self.nb_mfcs = nb_mfcs
        self.data_desc = ['unit', 'fs', 'sp', 'pv']
        self.pencolors = ['r', 'g', 'b']
        #self.mfcs = brooksSmartDDE(COM2,nb_mfcs) #test:nb_mfcs=1; R1:nb_mfcs=10
        #self.mfcs = brooksSProtocol(COM2,nb_mfcs) 
        # Create the main window
        self.setupUi(self)

        #création des listes de widgets:
        self.list_pv_widgets = [self.pv_1, self.pv_2, self.pv_3, self.pv_4, self.pv_5, self.pv_6, self.pv_7, self.pv_8, self.pv_9, self.pv_10]
        self.list_sp_widgets = [self.sp_1, self.sp_2, self.sp_3, self.sp_4, self.sp_5, self.sp_6, self.sp_7, self.sp_8, self.sp_9, self.sp_10]
        self.list_tag_widgets = [self.tag_1, self.tag_2, self.tag_3, self.tag_4, self.tag_5, self.tag_6, self.tag_7, self.tag_8, self.tag_9, self.tag_10]
        self.list_comport_widgets = [self.port_1, self.port_2, self.port_3, self.port_4, self.port_5, self.port_6, self.port_7, self.port_8, self.port_9, self.port_10]
        self.list_gase_widgets = [self.gaz_1, self.gaz_2, self.gaz_3, self.gaz_4, self.gaz_5, self.gaz_6, self.gaz_7, self.gaz_8, self.gaz_9, self.gaz_10]
        self.list_fullscale_widgets = [self.fs_1, self.fs_2, self.fs_3, self.fs_4, self.fs_5, self.fs_6, self.fs_7, self.fs_8, self.fs_9, self.fs_10]
        self.list_unit_widgets = [self.unit_1, self.unit_2, self.unit_3,  self.unit_4, self.unit_5, self.unit_6, self.unit_7, self.unit_8, self.unit_9, self.unit_10]

        #init listes des tags, comports, etc.:
        self.list_tags = [None]*MAX_INSTANCE_NUMBER
        self.list_comports = [None]*MAX_INSTANCE_NUMBER
        self.list_sps = [None]*MAX_INSTANCE_NUMBER
        self.list_fs = [None]*MAX_INSTANCE_NUMBER
        self.list_units = [None]*MAX_INSTANCE_NUMBER

        self.mfcs = [None]*MAX_INSTANCE_NUMBER #hardware MFCs or simulation

        # connexion des actions:
        self.actionConnect.triggered.connect(self.connectMFCs)

        # connexion des boutons
        self.pb_start.clicked.connect(self.start_data_streaming) #pas de parenthèses car on n'appelle pas la fonction
        self.pb_stop.clicked.connect(self.stop_data_streaming)

        # init les mfcs:
        self.connectMFCs()

    MSG_RE = r"[0-9]{8}" #https://www.regextester.com/97910
    MSG_RGX = re.compile(MSG_RE)

    def connectMFCs(self):
        result = QMessageBox.question(self,
                                                "Confirm Hardware mode...",
                                                "Do you want to quit simulation mode ans switch to hardware mode?",
                                                (QMessageBox.Yes |
                                                 QMessageBox.No))
        if result == QMessageBox.Yes:
            self.simulation_mode = False

        else:
            self.simulation_mode = True
        
        # lister les port disponibles:
        available_ports = comports()
        
        # fill comboBoxes with available ports
        for i in range(MAX_INSTANCE_NUMBER):
            for port in available_ports:
                l=[]
                for count in range(self.list_comport_widgets[i].count()):
                    l.append(self.list_comport_widgets[i].itemText(count))
                if port.device in l:
                    pass
                else:
                    self.list_comport_widgets[i].addItem(port.device)

            # initialiser le nom des gaz:
            self.__name_changed(i)
        
        self.isConnected = False
        self.pb_start.setEnabled(False)
        self.stop_data_streaming()
        for i in range(self.nb_mfcs):
            if self.simulation_mode:
                self.mfcs[i] = DoomyMFC()
                #self.isConnected = True
            else:
                self.list_tags[i] = self.list_tag_widgets[i].text()
                self.list_comports[i] = self.list_comport_widgets[i].currentText()
                if self.mfcs[i] is not None:
                    self.mfcs[i] = BrooksMFC(self.list_tags[i], self.list_comports[i])
                #self.isConnected = True
                #try:
                    #self.mfcs[i] = BrooksMFC(self.list_tags[i], self.list_comports[i])
                    #tag='28478010'
                    #self.mfcs[i] = BrooksMFC(tag,'COM4')
                    #print(self.mfcs[i].long_address)
                    #self.init_raw_data()
                    #self.connexion_and_init_plot()
                    #TODO: control instance creation when mfcs[i] is not None; test comm
                #except:
                    #e = sys.exc_info()[0]
                    #print( "Error: %s" % e )
                    #self.isConnected = False

        self.isConnected = True
        self.pb_start.setEnabled(True)
        self.on_init()
            
    def on_init(self):
        """
        personnalisation de l'interface
        """        
        if self.isConnected:
            # une méthode pour initialiser  le buffer de données
            self.init_raw_data()

            # une méthode pour intégrer les connexions
            # lors de l'utilisation des boutons
            # et insertion des tracer vides dans l'espace graphique
            self.connexion_and_init_plot()

        #self.h2EventSet.setContextMenuPolicy(Qt.CustomContextMenu)  # Configuration du doublespinbox: done in ui_*.py
        # connection for customContextMenu:
        #self.h2EventSet.customContextMenuRequested.connect(self.on_h2EventSet_customContextMenuRequested)

        # Création du menu custom
        self.custommenu = QMenu()
        self.custommenu.addAction("l/min")
        self.custommenu.addAction("cc/min")

    def init_raw_data(self, nb=10):
        """
        brooks data
        """
        self.RAW_DATA = {'time': None}
        self.current_names=[None]*MAX_INSTANCE_NUMBER
        for i in range(self.nb_mfcs):
            for name in self.data_desc:
                self.current_names[i] = self.list_gase_widgets[i].text()
                self.RAW_DATA[name+'_'+self.current_names[i]] = None

        self.RAW_DATA['time'] = [time.time()]
        
        for i in range(self.nb_mfcs):
            DATA = self.mfcs[i].get_all_data() # {'unit': str, 'fs': float, 'sp': float, 'pv': float}
            self.__unit_changed(i,DATA[self.data_desc[0]])
            self.list_fullscale_widgets[i].setText('FS = ' + '%.2f' % DATA[self.data_desc[1]])
            self.list_sp_widgets[i].setValue(DATA[self.data_desc[2]])
            self.list_pv_widgets[i].setText('%.2f' % DATA[self.data_desc[-1]])

            for name in self.data_desc[:-1]:
                self.RAW_DATA[name+'_'+self.current_names[i]] = DATA[name]
            self.RAW_DATA[self.data_desc[-1]+'_'+self.current_names[i]] = [DATA[self.data_desc[-1]]]
        print(i, DATA)
        while nb > 1:
            self.RAW_DATA['time'].append(time.time())
            for i in range(self.nb_mfcs):
                #DATA = self.mfcs[i].get_pv() # {'unit': str, 'fs': float, 'sp': float, 'pv': float}
                self.RAW_DATA[self.data_desc[-1]+'_'+self.current_names[i]].append(self.mfcs[i].get_pv())            
            nb -= 1

    def connexion_and_init_plot(self):
        # création des zones de tracer
        for i in range(self.nb_mfcs):
            if self.graphicsWindow.getItem(i,0) is None:
                self.graphicsWindow.addPlot(title=self.current_names[i])
                if i < self.nb_mfcs - 1:
                    self.graphicsWindow.nextRow()
        
                # création d'un plot dans chaque zt
                if hasattr(MainWindow, 'plt_zt'):
                    self.plt_zt.append(self.graphicsWindow.getItem(i,0).plot(
                        self.RAW_DATA[self.data_desc[-1]+
                            '_' + self.current_names[i]],
                        pen=self.pencolors[i %3])) # data_desc[-1] = plot 'pv'
                else:
                    self.plt_zt=[self.graphicsWindow.getItem(i,0).plot(
                        self.RAW_DATA[self.data_desc[-1]+
                            '_' + self.current_names[i]],
                        pen=self.pencolors[i %3])]

                #self.graphicsWindow.getItem(i,0).setTitle("other1_"+self.current_names[i])
                
    # connexion des unités
    def __unit_changed(self, idx, unit):
        self.list_unit_widgets[idx].setText(unit)
        self.list_sp_widgets[idx].setSuffix(' ' + unit)
        self.mfcs[idx].set_unit(unit)
    def on_unit_1_customContextMenuRequested(self, position):
        selectedItem = self.custommenu.exec_(self.unit_1.mapToGlobal(position))    
        if selectedItem:
            self.__unit_changed(0, selectedItem.text())            
    def on_unit_2_customContextMenuRequested(self, position):
        selectedItem = self.custommenu.exec_(self.unit_2.mapToGlobal(position))    
        if selectedItem:
            self.__unit_changed(1, selectedItem.text())
    def on_unit_3_customContextMenuRequested(self, position):
        selectedItem = self.custommenu.exec_(self.unit_3.mapToGlobal(position))    
        if selectedItem:
            self.__unit_changed(2, selectedItem.text())
    def on_unit_4_customContextMenuRequested(self, position):
        selectedItem = self.custommenu.exec_(self.unit_4.mapToGlobal(position))    
        if selectedItem:
            self.__unit_changed(3, selectedItem.text())
    def on_unit_5_customContextMenuRequested(self, position):
        selectedItem = self.custommenu.exec_(self.unit_5.mapToGlobal(position))    
        if selectedItem:
            self.__unit_changed(4, selectedItem.text())
    def on_unit_6_customContextMenuRequested(self, position):
        selectedItem = self.custommenu.exec_(self.unit_6.mapToGlobal(position))    
        if selectedItem:
            self.__unit_changed(5, selectedItem.text())
    def on_unit_7_customContextMenuRequested(self, position):
        selectedItem = self.custommenu.exec_(self.unit_7.mapToGlobal(position))    
        if selectedItem:
            self.__unit_changed(6, selectedItem.text())
    def on_unit_8_customContextMenuRequested(self, position):
        selectedItem = self.custommenu.exec_(self.unit_8.mapToGlobal(position))    
        if selectedItem:
            self.__unit_changed(7, selectedItem.text())
    def on_unit_9_customContextMenuRequested(self, position):
        selectedItem = self.custommenu.exec_(self.unit_9.mapToGlobal(position))    
        if selectedItem:
            self.__unit_changed(8, selectedItem.text())
    def on_unit_10_customContextMenuRequested(self, position):
        selectedItem = self.custommenu.exec_(self.unit_10.mapToGlobal(position))    
        if selectedItem:
            self.__unit_changed(9, selectedItem.text())

    # connexion des noms
    def __name_changed(self, idx):
        self.list_sp_widgets[idx].setPrefix(self.list_gase_widgets[idx].text() + " = ")
        if self.graphicsWindow.getItem(idx,0) is not None:
            self.graphicsWindow.getItem(idx,0).setTitle(self.list_gase_widgets[idx].text())
        if hasattr(MainWindow, 'RAW_DATA'):
            for name in self.data_desc:
                self.RAW_DATA[name+'_'+self.list_gase_widgets[idx].text()] = self.RAW_DATA.pop([name+'_'+self.current_names[idx]])
            self.current_names[idx] = self.list_gase_widgets[idx].text()            
    def on_gaz_1_editingFinished(self):
        self.__name_changed(0)
    def on_gaz_2_editingFinished(self):
        self.__name_changed(1)
    def on_gaz_3_editingFinished(self):
        self.__name_changed(2)
    def on_gaz_4_editingFinished(self):
        self.__name_changed(3)
    def on_gaz_5_editingFinished(self):
        self.__name_changed(4)
    def on_gaz_6_editingFinished(self):
        self.__name_changed(5)
    def on_gaz_7_editingFinished(self):
        self.__name_changed(6)
    def on_gaz_8_editingFinished(self):
        self.__name_changed(7)
    def on_gaz_9_editingFinished(self):
        self.__name_changed(8)
    def on_gaz_10_editingFinished(self):
        self.__name_changed(9)

    # connexion des tags
    def __tag_changed(self, idx):
        tag = self.list_tag_widgets[idx].text()
        tag = tag.split()[0]
        if len(tag) == 8:
            msg_match = self.MSG_RGX.match(tag)
            if msg_match:
                self.list_tags[idx] = msg_match.group()
    def on_tag_1_editingFinished(self):
        self.__tag_changed(0)
    def on_tag_2_editingFinished(self):
        self.__tag_changed(1)
    def on_tag_3_editingFinished(self):
        self.__tag_changed(2)
    def on_tag_4_editingFinished(self):
        self.__tag_changed(3)
    def on_tag_5_editingFinished(self):
        self.__tag_changed(4)
    def on_tag_6_editingFinished(self):
        self.__tag_changed(5)
    def on_tag_7_editingFinished(self):
        self.__tag_changed(6)
    def on_tag_8_editingFinished(self):
        self.__tag_changed(7)
    def on_tag_9_editingFinished(self):
        self.__tag_changed(8)
    def on_tag_10_editingFinished(self):
        self.__tag_changed(9)

    # connexion des setpoints:
    def __setpointchange(self, idx):
        self.list_sps[idx] = self.list_sp_widgets[idx].value()
        self.mfcs[idx].set_setpoint(self.list_sp_widgets[idx].value())
        #TODO: if not simulation_mode: send to MFC
    def on_sp_1_valueChanged(self):
        self.__setpointchange(0)
    def on_sp_2_valueChanged(self):
        self.__setpointchange(1)
    def on_sp_3_valueChanged(self):
        self.__setpointchange(2)
    def on_sp_4_valueChanged(self):
        self.__setpointchange(3)
    def on_sp_5_valueChanged(self):
        self.__setpointchange(4)
    def on_sp_6_valueChanged(self):
        self.__setpointchange(5)
    def on_sp_7_valueChanged(self):
        self.__setpointchange(6)
    def on_sp_8_valueChanged(self):
        self.__setpointchange(7)
    def on_sp__valueChanged(self):
        self.__setpointchange(8)
    def on_sp_10_valueChanged(self):
        self.__setpointchange(9)

    #connexion des comports:
    def __comportchange(self, idx):
        if self.list_comport_widgets[idx].currentIndex() != 0:
            self.list_comports[idx] = self.list_comport_widgets[idx].currentText()    
    def on_port_1_valueChanged(self):
        self.__comportchange(0)
    def on_port_2_valueChanged(self):
        self.__comportchange(1)
    def on_port_3_valueChanged(self):
        self.__comportchange(2)
    def on_port_4_valueChanged(self):
        self.__comportchange(3)
    def on_port_5_valueChanged(self):
        self.__comportchange(4)
    def on_port_6_valueChanged(self):
        self.__comportchange(5)
    def on_port_7_valueChanged(self):
        self.__comportchange(6)
    def on_port_8_valueChanged(self):
        self.__comportchange(7)
    def on_port_9_valueChanged(self):
        self.__comportchange(8)
    def on_port_10_valueChanged(self):
        self.__comportchange(9)

    def start_data_streaming(self):
        if self.mon_timer is None and self.isConnected:
            self.mon_timer = self.startTimer(self.period_timer)
    
    def stop_data_streaming(self):
        if self.mon_timer is not None:
            self.killTimer(self.mon_timer)
            self.mon_timer = None

    def timerEvent(self, _):        
        t = time.time()
        
        self.RAW_DATA['time'] = np.roll(self.RAW_DATA['time'], -1)
        self.RAW_DATA['time'][-1] = t
        #DATA = self.mfcs.get_all_data()
        
        #roll RAW_DATA:
        for i in range(self.nb_mfcs):
            DATA = self.mfcs[i].get_all_data() # {'unit': str, 'fs': float, 'sp': float, 'pv': float}
            self.RAW_DATA[self.data_desc[-1]+'_'+self.current_names[i]] = np.roll(self.RAW_DATA[self.data_desc[-1]+'_'+self.current_names[i]],-1)
            self.RAW_DATA[self.data_desc[-1]+'_'+self.current_names[i]][-1] = DATA[self.data_desc[-1]]

            self.list_pv_widgets[i].setText('%.2f' % DATA[self.data_desc[-1]])
            self.plt_zt[i].setData(self.RAW_DATA[self.data_desc[-1]+
                '_'+self.current_names[i]])

    def closeEvent(self, event):
        """
        doc string
        """
        # ajoute une boite de dialogue pour confirmation de fermeture
        result = QMessageBox.question(self,
                                                "Confirm Exit...",
                                                "Do you want to exit ?",
                                                (QMessageBox.Yes |
                                                 QMessageBox.No))
        if result == QMessageBox.Yes:
            # permet d'ajouter du code pour fermer proprement
            event.accept()
        else:
            event.ignore()


if __name__ == '__main__':    
    app = QApplication([])
    #pg.setConfigOption('background', '#505050')
    #dark_stylesheet = qdarkstyle.load_stylesheet_pyqt5()
    
    #app.setStyleSheet(dark_stylesheet)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
