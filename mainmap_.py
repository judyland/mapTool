
import pandas as pd
import random
import geopandas as gpd
import plotly
import numpy
from geopandas.tools import overlay
from geopandas import GeoDataFrame
from geopandas import points_from_xy
import heapq as heapg
import matplotlib.pyplot as plt
#import utn
from matplotlib import animation
import math
import sys
from PyQt6 import QtCore
from PyQt6.QtWidgets import *
from PyQt6 import QtGui
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from configparser import ConfigParser
from mainwindow_ui import Ui_MainWindow
import copy
#import rosterio
import mapeditor_rc
import os

class MplWidget(QWidget):
    def __init__(self,  parent=None):
        QWidget.__init__(self,  parent)

        global myFigure
        self.canvas = FigureCanvas (myFigure)
        self.canvas.resize (1000,  600)
        self.canvas.axes = self.canvas.figure.add_subplot(111)
        self.canvas.axes.set(title='Israel map', xlim = [33, 38], ylim = [28,34])

        self.dataframes = []
        self.canvas.draw()


    def addLayer (self, fname, color):
        if fname.endswith(".shp"):
            map_latlon = gpd.read_file(fname)
            p  = map_latlon.plot(ax=self.canvas.axes, color = color)
            return
        elif fname.endswith(".csv"):
            df = pd.read_csv(fname)

        elif fname.endswith(".json"):
            df = pd.read_json(fname)

        self.dataframes.append(df)
        geom = points_from_xy(df['long'], df['lat'])
        self.gdf = gpd.GeoDataFrame(copy.deepcopy(df), geometry=geom)

        if 'route' in df.columns:
            if 'r/d' in df.columns:
                gdf_f = self.gdf[self.gdf["r/d"] == "r"]
            else:
                gdf_f = self.gdf
            lines_array = gdf_f.groupby(['route'])
            groups = lines_array.indices
            for gr in groups:
                route = lines_array.get_group(gr)
                route.insert(1, 'path', 0)
                route.plot.line(ax=self.canvas.axes, c=numpy.random.random(3),x='long', y='lat')
                self.gdf.plot(ax=self.canvas.axes, color='red', marker='o')
        else:
            self.gdf.plot(ax=self.canvas.axes, color='red', marker='*')


        ls = self.gdf['geometry'].geom_type
        if 'Point' == list(ls)[0]:
            for x, y, label in zip (self.gdf.geometry.x, self.gdf.geometry.y, self.gdf.name) :
                self.canvas.axes.annotate (label, xy= (x, y), xytext=(3, 3),textcoords="offset points")
        self.canvas.draw()


current_df = pd.DataFrame({'r/d':[], 'route':[], 'order':[], 'name': [], 'long': [], 'lat':[]})
myFigure = Figure()


class ObjectsModel(QAbstractTableModel):
    def __init__(self, parent=None) :
        super().__init__(parent)

    def rowCount(self, parent):
        return len(current_df.index)

    def columnCount(self, parent):
        return len(current_df.columns)

    def headerData(self, col, orientation=Qt.Orientation.Horizontal, role=None):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            if col >= len(current_df.columns):
                return ''
            return str(current_df.columns[col])

    def data(self, modelIndex, role=None):
        if role == Qt.ItemDataRole.DisplayRole and modelIndex.row() < len(current_df):
            return str(current_df.iat[modelIndex.row(), modelIndex.column()])

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsEnabled
        return super().flags(index) | Qt.ItemFlag.ItemIsEditable  # add editable flag.

    def setData(self, modelIndex, any, role=None):
        current_df.iat[modelIndex.row(), modelIndex.column()] = any
        return True

class MplMainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super (MplMainWindow, self).__init__()
        super ().__init__(parent)
        pix = QtGui.QPixmap(":/res/ui/edit.png")
        self.setupUi(self)
        self.mplw = MplWidget()
        self.connectSignalsSlots()
        self.addToolBar (NavigationToolbar (self.mplw.canvas, self))

        self.gridLayoutMap.addWidget (self.mplw.canvas, 0, 0, 1, 1)
        self.pointsModel = ObjectsModel(self)
        self.tableViewEditor.setModel(self.pointsModel)
        self.route = 0
        self.order = 0
        self.cid = 0

    def connectSignalsSlots (self):
        self.actionOpen_Layer.triggered.connect (self.openMap)
        self.actionRemove_Layer.triggered.connect (self.removeLayer)
        self.actionAddPoint.triggered.connect (self.addPoint)
        self.actionAddLine.triggered.connect (self.addLine)
        self.pushButtonAddLayer.clicked.connect (self.openMap)
        self.pushButtonRemoveLayer.clicked.connect (self.removeLayer)
        self.pushButtonEditLayer.clicked.connect(self.editLayer)
        self.pushButtonSaveAs.clicked.connect (self.saveAs)
        self.pushButtonSave.clicked.connect (self.save)
        self.pushButtonClean.clicked.connect (self.clean)
        self.doubleSpinBoxLongitude.valueChanged.connect (self.setExtent)
        self.doubleSpinBoxLatitude.valueChanged.connect (self.setExtent)
        self.doubleSpinBoxExtent.valueChanged.connect (self.setExtent)
        self.pushButtonGetCenter.clicked.connect (self.getCenter)
        self.listWidget.itemClicked.connect(self.itemSelected)

    def itemSelected(self):
        self.pushButtonEditLayer.setEnabled(True)

    def  getCenter (self):
        xc  =  (self.mplw.canvas.axes.viewLim.x0  +  self.mplw.canvas.axes.viewLim.x1) / 2
        yc  =  (self.mplw.canvas.axes.viewLim.y0  +  self.mplw.canvas.axes.viewLim.y1) / 2
        ext  =  self.mplw.canvas.axes.viewLim.x1  -  self.mplw.canvas.axes.viewLim.x0

        self.doubleSpinBoxLongitude.setValue(xc)
        self.doubleSpinBoxLatitude.setValue(yc)
        self.doubleSpinBoxExtent.setValue(ext)


    def setExtent (self):
       config = ConfigParser()
       config.read('maper.ini')
       lon = self.doubleSpinBoxLongitude.value()
       lat = self.doubleSpinBoxLatitude.value()
       extent = self.doubleSpinBoxExtent.value()
       config['EXTENT'] = {"longitude": lon,
                           "latitude": lat,
                           "extent": extent}
       with open('maper.ini', 'w') as configfile:
            config.write(configfile)
       self.mplw.canvas.axes.set(xlim=[lon - extent/2,  lon + extent/2],
                                 ylim=[lat - extent/2,  lat + extent/2])
       self.mplw.canvas.draw()

# utm 36N


    def openMap (self):
        fname = QFileDialog.getOpenFileName (filter="Shape Files (*.shp);; CSV Files (*.csv);; JSON Files(*.json)")
        self.mplw.addLayer (fname [0], 'black')
        if self.flist.count(fname) == 0:
            self.flist.append(fname[0])
        self.listWidget.addItem(os.path.relpath(fname[0], os.curdir))
        fstring = '\n'.join(self.flist)
        config= ConfigParser()
        config.read('maper.ini')
        if config.sections() == []:
            config['MAPFILES'] = {"filelist": ""}
        config['MAPFILES']['filelist'] = fstring
        with open('maper.ini', 'w') as configfile:
            config.write(configfile)

    def  editLayer(self):
        n = self.listWidget.currentRow()
        self.currentFile  = self.listWidget.item(n).text()
        self.labelLayer.setText (self.currentFile)
        global current_df
        df =  self.mplw.dataframes [n]
        type = 'n'
        if 'route' not in df.columns:
            type = 'd'
        elif 'r/d' not in df.columns:
            type = 'r'
        current_df = pd.DataFrame({'r/d':[], 'route':[], 'order':[], 'name': [], 'long': [], 'lat':[]})
        current_df = current_df.merge(df, how = 'outer').fillna(value = {'r/d':type, 'route':'0', 'order':'0'})
        n = self.tableViewEditor.model().rowCount(QModelIndex())
        self.tableViewEditor.model().beginRemoveRows (QModelIndex(),   0,   n)
        self.tableViewEditor.model().endRemoveRows()

        n =  len (current_df)
        self.tableViewEditor.model().beginInsertRows (QModelIndex(),   0,   n-1)
        self.tableViewEditor.model().endInsertRows()
        self.tabWidget.setCurrentIndex(1)
        self.order = n
        self.route = current_df.iloc[n-1]['route']

    def removeLayer (self):
        n = self.listWidget.currentRow()
        self.listWidget.takeItem(n)
        config = ConfigParser()
        config.read('maper.ini')
        s = config.sections ()
        self.mplw.dataframes.clear()
        items = []
        for i in range (self.listWidget.count()):
            items.append(self. listWidget.item(i).text())
        fstring = '\n'.join(items)
        config['MAPFILES'] = {"filelist": fstring}
        with open('maper.ini', 'w') as configfile:
            config.write(configfile)
        self.displayMaps ()


    def addNode(self, x, y, type):
        n = len(current_df)
        self.tableViewEditor.model().beginInsertRows(QModelIndex(), n, n)
        current_df.loc[len(current_df.index)] = [type, self.route, self.order,
                                                 'Node-'+str(self.route)+'-'+str(self.order),
                                                 f'{x:.4f}',  f'{y:.4f}']
        self.tableViewEditor.model().endInsertRows()
        self.order += 1

    def addPoint (self, set):
        if self.cid > 0:
            self.mplw.canvas.mpl_disconnect (self.cid)

        self.cid = self.mplw.canvas.mpl_connect('button_press_event', self.getPoint)
        self.mplw.canvas.setCursor(Qt.CursorShape.CrossCursor)

    def getPoint (self, event):  # press event
        ix, iy = event.xdata, event.ydata
        self.mplw.canvas.axes.plot(ix, iy, '+', color='red', markersize=10)
        self.mplw.canvas.draw()
        self.mplw.canvas.draw()
        self.mplw.canvas.setCursor (Qt.CursorShape.CrossCursor)
        n = len (current_df)
        self.addNode(ix, iy, 'd')

    def addLine(self, set):  # starting line
        if self.cid > 0:
            self.mplw.canvas.mpl_disconnect (self.cid)

        self.x_start, self.y_start = 0, 0
        self.cid= self.mplw.canvas.mpl_connect('button_press_event', self.getLineStart)
        self.mplw.canvas.setCursor(Qt.CursorShape.UpArrowCursor)

        self.mplw.canvas.draw()
        self.route += 1

    def getLineStart (self, event):  # press event
        if event.button == 3:
            self.line_add =  False
            return

        self.x_start, self.y_start = event.xdata, event.ydata
        self.mplw.canvas.axes.plot(self.x_start, self.y_start, 'o', c=numpy.random.random(3), markersize=7)
        self.mplw.canvas.draw()
        self.line_add = True
        self.cid_release = self.mplw.canvas.mpl_connect('button_release_event', self.stopLine)
        self.mplw.canvas.mpl_connect('motion_notify_event', self.getLineEnd)
        self.prev, = self.mplw.canvas.axes.plot([self.x_start, self.x_start],
                                                [self.y_start, self.y_start],
                                                c=numpy.random.random(3))
        self.mplw.canvas.setCursor(Qt.CursorShape.UpArrowCursor)
        n = len(current_df)
        self.addNode(self.x_start, self.y_start, 'r')

    def getLineEnd(self, event):  # move event
        if self.line_add :
            self.prev.remove()
            x, y = event.xdata, event.ydata
            self.prev, = self.mplw.canvas.axes.plot([self.x_start, x], [self.y_start, y], c=numpy.random.random(3))
            self.mplw.canvas.draw()

    def stopLine (self, event):  # release event
        x, y = event.xdata, event.ydata
        self.mplw.canvas.axes.plot(x, y, '.', color='green', markersize=7)
        self.x_start, self.y_start = x, y
        self.prev, = self.mplw.canvas.axes.plot([x, x], [y, y], color='green')
        self.mplw.canvas.mpl_disconnect (self.cid_release)
        self.mplw.canvas.draw()
        self.mplw.canvas.setCursor(Qt.CursorShape.UpArrowCursor)

    def displayMaps (self):
        config = ConfigParser()
        config.read('maper.ini')
        s = config.sections()
        if config.sections() == []:
            config['MAPFILES'] = {"filelist": ""}
        fliststr = config.get('MAPFILES', 'filelist')
        self. flist=fliststr.splitlines()
        self.listWidget.clear()
        self.listWidget.addItems (self.flist)
        colors= ['black','green', 'blue', 'red','gray','yellow']
        self.mplw.canvas.axes.clear()

        if  not  config.has_section ('EXTENT')  :
                config['EXTENT']  =  {"longitude":  35,
                "latitude":  32,
                "extent":  6}
        lon  =  float(config.get('EXTENT',  'longitude'))
        lat  =  float(config.get('EXTENT',   'latitude'))

        extent  =  float(config.get('EXTENT',  'extent'))
        self.doubleSpinBoxLongitude.valueChanged.disconnect (self.setExtent)
        self.doubleSpinBoxLatitude.valueChanged.disconnect (self.setExtent)
        self.doubleSpinBoxExtent.valueChanged.disconnect (self.setExtent)

        self.doubleSpinBoxLongitude.setValue (lon)
        self.doubleSpinBoxLatitude.setValue(lat)
        self.doubleSpinBoxExtent.setValue(extent)

        self.doubleSpinBoxLongitude.valueChanged.connect (self.setExtent)
        self.doubleSpinBoxLatitude.valueChanged.connect (self.setExtent)
        self.doubleSpinBoxExtent.valueChanged.connect (self.setExtent)

        self.mplw.canvas.axes.set(title='Israel  map',  xlim=[lon  -  extent/2,  lon + extent/2],
                                                        ylim=[lat  -  extent/2,   lat  +  extent/2])
        i =  0
        for  f  in  self.flist  :
            if  i  ==  len(colors):
                i = 0
            self.mplw.addLayer (f,   colors[i])
            i = i  + 1
        self.mplw.canvas.draw()
        self.pushButtonSave.setEnabled(False)
        self.pushButtonEditLayer.setEnabled(False)

    def  saveFile(self, fname):
            if fname.endswith("csv"):
                current_df.to_csv (fname,   index=False)
            elif fname.endswith("json"):
                current_df.to_json (fname)

    def  save(self):
            self.saveFile(self.currentFile)

    def  clean(self):
            global current_df
            current_df = current_df.drop(current_df.index[0:])

            for _row in range(self.tableViewEditor.model().rowCount(QModelIndex())):
                self.tableViewEditor.hideRow(_row)

            self.tableViewEditor.reset()
            #self.displayMaps()

    def  saveAs(self):
            fname  =  QFileDialog.getSaveFileName (filter="CSV  File(*.csv);; JSON File(*.json)")
            self.saveFile(fname[0])

def init():
    return([])

def animate(i):
    global prev
    s = i* 0.05
    x = 36 + s
    y = 34 - s
    prev.remove()
    prev, = win.mplw.canvas.axes.plot(x, y, 's', color='red', markersize=12)
    return ([])


#fig, ax = plt.subplots()

print (__name__)
if __name__ == "__main__":
    app = QApplication(sys.argv)
    plt. tight_layout()
    win = MplMainWindow()


    prev, = win.mplw.canvas.axes.plot(34, 31, '.', c=numpy.random.random(3), markersize=12)
    #am = animation.FuncAnimation (myFigure, animate, init_func=init, frames=100, interval=588)
    win.displayMaps ()
    win.show()
    sys.exit(app.exec())