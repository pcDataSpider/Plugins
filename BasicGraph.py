import wx
import wx.lib.plot
import logger
import time
import threading
import Queue

import os, sys
#import graph






title = "Graphing tool"
description = "Graphs an analog input values"

UPDATEINTERVAL = 0.5



def run_tool(window_parent, device):
	# ask user for selected channels
	choices = []
	channels = []
	plotChannels = []
	for key, c in device.analogIn.iteritems():
		choices.append( "Analog input " + str(c.idx) )
		channels.append( c )

	dlg = wx.MultiChoiceDialog(window_parent, message="Select which inputs to sample", caption="Input Selection", choices=choices)
	dlg.SetSelections([0])
	if dlg.ShowModal()== wx.ID_OK:
		selection = dlg.GetSelections()
		for idx in selection:
			plotChannels.append( channels[idx] )
	else:
		return
        dlg.Destroy() 

	# get graph simensions
	info = GraphInfoBox(window_parent,xRange=(0,100),yRange=(0,4096))
	if info.ShowModal() == wx.ID_OK:
		if len(plotChannels) > 1:
			chanNames = "Analogs "
		else:
			chanNames = "Analog "
		for c in plotChannels[:-1]:
			chanNames += str(c.idx) + ", "
		chanNames += str(plotChannels[-1].idx) 
		wnd = NewGraphFrame(window_parent, device, channels=plotChannels, nAvg=1, xRange=info.xRange, yRange=info.yRange, title= "Graph - " + chanNames )
		wnd.Show()

		
colorTable = [ "blue", "red", "green", "yellow", "purple", "black" ]
	
class GraphFrame(wx.Frame):
	def __init__(self, parent, xRange=None, yRange=None, xSize=None, ySize=None, nPoints=None, header=None,  title="Graph", xlabel="Seconds", ylabel="Value", showPoints=False, POINTDEBUG=False):
		self.max_X = xSize
		self.max_Y = ySize
		self.xRange = xRange
		self.yRange = yRange
		self.nPoints = nPoints
		self.showPoints = showPoints
		self.POINTDEBUG = POINTDEBUG



		if self.nPoints is not None:
			self.dataQueue = Queue.Queue(self.nPoints)

		self.title = title
		self.xlabel = xlabel
		self.ylabel = ylabel
		self.outFile = None
		self.header = header
		if self.header is None:
			date = '"' + time.asctime() + '"'
			self.header = date

		wndsize = wx.Size(500,500)

		self.pending = False

		# initialize frame object
		wx.Frame.__init__(self, parent, id=wx.ID_ANY, title=self.title , pos=wx.DefaultPosition, size=wndsize)
		ico = wx.Icon('OFSI-Logo.ico', wx.BITMAP_TYPE_ICO )
		self.SetIcon( ico )

		# add menubar
		self.menuBar = wx.MenuBar( 0 )
		self.fileMenu = wx.Menu()
		self.editMenu = wx.Menu()
		self.menuBar.Append(self.fileMenu, "File")
		self.menuBar.Append(self.editMenu, "Edit")
		# create menu items
		save = wx.MenuItem( self.fileMenu, wx.ID_ANY, "Save", "Saves the current graph", wx.ITEM_NORMAL )
		close = wx.MenuItem( self.fileMenu, wx.ID_ANY, "Close", "Closes the graph window", wx.ITEM_NORMAL )
		setAxis = wx.MenuItem( self.fileMenu, wx.ID_ANY, "Dimensions", "Changes the graph dimensions", wx.ITEM_NORMAL )
		# append menu items
		self.fileMenu.AppendItem(save)
		self.fileMenu.AppendItem(close)
		self.editMenu.AppendItem(setAxis)
		# bind items
		self.Bind( wx.EVT_MENU, self.OnClose, id=close.GetId() )
		self.Bind( wx.EVT_MENU, self.OnResize, id=setAxis.GetId() )
		self.Bind( wx.EVT_MENU, self.OnSave, id=save.GetId() )
		self.SetMenuBar( self.menuBar)
	
		# add plot
		self.mainSizer = wx.BoxSizer(wx.VERTICAL)
		self.plot = wx.lib.plot.PlotCanvas(self, size=wx.Size(500,500), style=wx.EXPAND)
		self.plot.SetShowScrollbars(True)

		# add points
		self.data = dict()
		self.displayData = dict()
		if self.max_X is not None:
			lastX = self.max_X/2.0 
		elif self.xRange is not None:
			lastX = xRange[0]
		else:
			lastX = 0
		if self.max_Y is not None:
			lastY = self.max_Y/2.0
		elif self.yRange is not None:
			lastY = yRange[0]
		else:
			lastY = 0

		self.lastpoint = (lastX, lastY)
		self.updateTimer = None

		self.mainSizer.Add(self.plot, 1, wx.EXPAND, 0)
		self.SetSizer(self.mainSizer)
		self.Layout

		self.Bind(wx.EVT_CLOSE,self.OnClose)

	

	def updateData(self):

		lines = []
		if not self.data:
			lines.append( wx.lib.plot.PolyLine([self.lastpoint], colour="black", width=1) )
		else:
			n = 0
			for idx in self.data:
				thisColor = colorTable[n]
				n += 1
				if self.showPoints:
					if self.nPoints > 0:
						lines.append( wx.lib.plot.PolyMarker(self.displayData[idx], colour=thisColor, width=2, fillstyle=wx.SOLID, fillcolour=thisColor, size=1, marker="circle") )
					else:
						lines.append( wx.lib.plot.PolyMarker(self.data[idx], colour=thisColor, width=2, fillstyle=wx.SOLID, fillcolour=thisColor, size=1, marker="circle") )
				if self.nPoints > 0:
					lines.append( wx.lib.plot.PolyLine(self.displayData[idx], colour=thisColor, legend=str(idx), width=1) )
				else:
					lines.append( wx.lib.plot.PolyLine(self.data[idx], colour=thisColor, legend=str(idx), width=1) )
				#lines.append( wx.lib.plot.PolyLine(self.dataQueue, colour="green", width=1) )
		pg = wx.lib.plot.PlotGraphics(lines, self.title, self.xlabel, self.ylabel)
		if self.max_X is not None:
			self.xRange = ( self.lastpoint[0] - self.max_X/2.0, self.lastpoint[0] + self.max_X/2.0 )
		if self.max_Y is not None:
			self.yRange = ( self.lastpoint[1] - self.max_Y/2.0, self.lastpoint[1] + self.max_Y/2.0 )
		
		if len( self.data ) > 1 :
			self.plot.SetEnableLegend(True)
		self.plot.Draw(pg, self.xRange, self.yRange)
		self.pending = False
		
	
	def addPoint(self, x, y, idx, debugObj=None):
		if idx not in self.data:
			self.data[idx] = []
			self.displayData[idx] = []
		self.data[idx].append((x,y,debugObj))
		self.displayData[idx].append((x,y))
		#if self.dataQueue.full():
		#	self.dataQueue.get()
		#self.dataQueue.put((x,y))
		#if self.nPoints > 0:
		#	self.xRange = 
		if self.nPoints > 0:
			tPoints = 0
			for c in self.displayData:
				tPoints += len( self.displayData[c] )

			if tPoints > self.nPoints:
				self.displayData[idx].pop(0)

		self.lastpoint = (x,y)
		if not self.pending:
			self.pending = True
			def update():
				self.updateData()
			self.updateTimer = threading.Timer(.5,update)
			self.updateTimer.start()
	def OnResize(self, event):
		info = GraphInfoBox(self, xRange=self.xRange, yRange=self.yRange, xunits=self.xlabel, yunits=self.ylabel) 
		if info.ShowModal() == wx.ID_OK:
			self.xRange = info.xRange
			self.yRange = info.yRange
		self.updateData()

	def OnSave(self, event):
		filetypes = "CSV files (*.csv)|*.csv|Text files (*.txt)|*.txt|All files|*"
		dlg = wx.FileDialog(self, "Choose a file", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT, wildcard=filetypes)
		outFile = None
		if dlg.ShowModal()==wx.ID_OK:
			try:
				filename=dlg.GetFilename()
				dirname=dlg.GetDirectory()
				fullPath = os.path.join(dirname, filename)	
				self.SetTitle( self.title + " - " + filename )
				outFile = open(fullPath, "w")
				# write header info
				outFile.write( self.header )
				outFile.write( "\n" )
				for idx in self.data:
					outFile.write(", X" + str(idx) )
					outFile.write(", Y" + str(idx) )
					if self.POINTDEBUG:
						outFile.write(", DEBUG" + str(idx) )
				outFile.write( "\n" )
				# write data
				nData = 0
				for idx in self.data:
					if len(self.data[idx]) > nData:
						nData = len( self.data[idx] )
				for n in range( nData ):
					for idx in self.data:
						try:
							strfmt = ",{0:.5f},{1}".format(self.data[idx][n][0], self.data[idx][n][1])
							if self.POINTDEBUG:
								strfmt += "," + str(self.data[idx][n][2])
							outFile.write(strfmt)
						except IndexError:
							pass
					outFile.write( "\n")
				outFile.close()
			except IOError as e:
				logger.log("Error opening file", e, logger.WARNING)
				logger.message("Error opening file.", logger.ERROR)
			except ValueError as e:
				logger.log("Error writing file", e, logger.WARNING)
				logger.message("Error writing file.", logger.ERROR)
		dlg.Destroy()



	def OnClose(self, event):
		if self.updateTimer is not None: self.updateTimer.cancel()
		self.Destroy()




class GetNumBox(wx.Dialog):
	def __init__(self, parent, xRange = None, prompt="Number", title="Num", text=""):
		wx.Dialog.__init__(self, parent, id=wx.ID_ANY, title = "Enter A Number")





class GraphInfoBox(wx.Dialog):
	def __init__(self, parent, xRange=(0,100), yRange=(0,100), xmin=0, xmax=99999999, ymin=0, ymax=4096, xunits="Seconds", yunits="units"):
		wx.Dialog.__init__ ( self, parent, id = wx.ID_ANY, title = "Graph Information"  )
		ico = wx.Icon('OFSI-Logo.ico', wx.BITMAP_TYPE_ICO )
		self.SetIcon( ico )
		xcheck = False
		ycheck = False
		if xRange is None:
			xcheck = True
			xRange = (0,0)
		if yRange is None:
			ycheck = True
			yRange = (0,0)
		# -- create window controls --
		self.mainSizer = wx.BoxSizer( wx.VERTICAL )
		self.mainSizer.AddSpacer( ( 0, 10), 0, wx.EXPAND, 5 )
		txt2 = wx.StaticText( self, wx.ID_ANY, "Graph Dimensions:", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.mainSizer.Add( txt2, 0, wx.LEFT|wx.TOP, 10 )
		
		axisSplit = wx.BoxSizer( wx.HORIZONTAL )
		xSizer = wx.BoxSizer( wx.VERTICAL )
		ySizer = wx.BoxSizer( wx.VERTICAL )
		axisSplit.Add( xSizer, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 15)
		axisSplit.Add( ySizer, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 15)
		self.mainSizer.Add(axisSplit, 0, wx.ALL, 5)

		# add controls for x axis
		xdimSizer = wx.BoxSizer( wx.HORIZONTAL )
		self.xLower = wx.TextCtrl( self, wx.ID_ANY, str(xRange[0]), wx.DefaultPosition, wx.Size( 45,-1 ), 0 )
		self.xUpper = wx.TextCtrl( self, wx.ID_ANY, str(xRange[1]), wx.DefaultPosition, wx.Size( 45,-1 ), 0 )
		xtxt2 = wx.StaticText( self, wx.ID_ANY, " - " , wx.DefaultPosition, wx.DefaultSize, 0 )
		xdimSizer.Add( self.xLower, 1, wx.BOTTOM, 5 )
		xdimSizer.Add( xtxt2, 0, 0, 5 )
		xdimSizer.Add( self.xUpper, 1, wx.BOTTOM, 5 )

		if xunits is not None:
			xtitle = "X Axis (" + xunits + ") :"
		else:
			xtitle = "X Axis :"
		xtxt = wx.StaticText( self, wx.ID_ANY, xtitle , wx.DefaultPosition, wx.DefaultSize, 0 )

		self.xautoScale = wx.CheckBox(self, wx.ID_ANY, "Autoscale", wx.DefaultPosition, wx.DefaultSize, 0)
		self.xautoScale.SetValue(xcheck)

		xSizer.Add(xtxt, 0, wx.ALL, 5)
		xSizer.Add(xdimSizer, 0, wx.ALL, 5)
		xSizer.Add(self.xautoScale, 0, wx.LEFT, 10)

		# add controls for y axis
		ydimSizer = wx.BoxSizer( wx.HORIZONTAL )
		self.yLower = wx.TextCtrl( self, wx.ID_ANY, str(yRange[0]), wx.DefaultPosition, wx.Size( 45,-1 ), 0 )
		self.yUpper = wx.TextCtrl( self, wx.ID_ANY, str(yRange[1]), wx.DefaultPosition, wx.Size( 45,-1 ), 0 ) 
		ytxt2 = wx.StaticText( self, wx.ID_ANY, " - " , wx.DefaultPosition, wx.DefaultSize, 0 )
		ydimSizer.Add( self.yLower, 1, wx.BOTTOM, 5 )
		ydimSizer.Add( ytxt2, 0, wx.BOTTOM, 5 )
		ydimSizer.Add( self.yUpper, 1, wx.BOTTOM, 5 )

		if yunits is not None:
			ytitle = "Y Axis (" + yunits + ") :"
		else:
			ytitle = "Y Axis :"
		ytxt = wx.StaticText( self, wx.ID_ANY, ytitle , wx.DefaultPosition, wx.DefaultSize, 0 )

		self.yautoScale = wx.CheckBox(self, wx.ID_ANY, "Autoscale", wx.DefaultPosition, wx.DefaultSize, 0)
		self.yautoScale.SetValue(ycheck)
		ySizer.Add(ytxt, 0, wx.ALL, 5)
		ySizer.Add(ydimSizer, 0, wx.ALL, 5)
		ySizer.Add(self.yautoScale, 0, wx.LEFT, 10)

	

		# add OK/Cancel button controls
		#btnSizer = self.CreateButtonSizer( wx.OK | wx.CANCEL )
		btnSizer = wx.BoxSizer( wx.HORIZONTAL )
		okBtn = wx.Button( self, wx.ID_ANY, "OK", wx.DefaultPosition, wx.DefaultSize, 0 )
		cancelBtn = wx.Button( self, wx.ID_ANY, "Cancel", wx.DefaultPosition, wx.DefaultSize, 0 )
		btnSizer.Add( okBtn, 1, wx.ALIGN_RIGHT, 5 )
		btnSizer.Add( cancelBtn, 1, wx.ALIGN_RIGHT, 5 )
		self.mainSizer.Add( btnSizer, 1, wx.ALIGN_RIGHT, 5 )
		# set default buttons
		self.SetAffirmativeId(okBtn.GetId())
		self.SetEscapeId(cancelBtn.GetId())
		
		self.SetSizer( self.mainSizer )
		self.Layout()
		self.Fit()
		
		self.Centre( wx.BOTH )
		self.On_X_Autoscale(None)
		self.On_Y_Autoscale(None)

		# -- Connect Events --
		self.xautoScale.Bind( wx.EVT_CHECKBOX, self.On_X_Autoscale )
		self.yautoScale.Bind( wx.EVT_CHECKBOX, self.On_Y_Autoscale )
		okBtn.Bind( wx.EVT_BUTTON, self.On_OK )
		cancelBtn.Bind( wx.EVT_BUTTON, self.On_Cancel )
		self.Bind( wx.EVT_CLOSE, self.On_Close )
	def On_Y_Autoscale(self, event):
		enabled = not self.yautoScale.GetValue()
		self.yLower.Enable( enabled )
		self.yUpper.Enable( enabled )
	def On_X_Autoscale(self, event):
		enabled = not self.xautoScale.GetValue()
		self.xLower.Enable( enabled )
		self.xUpper.Enable( enabled )

	def On_Close(self, event):
		self.EndModal(wx.ID_CANCEL)
		pass	

	def On_Cancel(self, event):
		self.EndModal(wx.ID_CANCEL)

	def On_OK(self, event):
		if self.xautoScale.GetValue():
			self.xRange = None
		else:
			try:
				self.xMin = float(self.xLower.GetValue())
			except ValueError:
				self.xMin = 0
			try:
				self.xMax = float(self.xUpper.GetValue())
			except ValueError:
				self.xMin = 0
				self.xMax = 0
			self.xRange = (self.xMin, self.xMax )

		if self.yautoScale.GetValue():
			self.yRange = None
		else:
			try:
				self.yMin = float(self.yLower.GetValue())
			except ValueError:
				self.yMin = 0
			try:
				self.yMax = float(self.yUpper.GetValue())
			except ValueError:
				self.yMin = 0
				self.yMax = 0
			self.yRange = (self.yMin, self.yMax )


		self.EndModal(wx.ID_OK)
	

	



	
class NewGraphFrame( GraphFrame):
	def __init__(self, parent, device, channels=None, xRange=None, yRange=None, xSize=None, ySize=None, nAvg=1, title="Graph", xlabel="Seconds", ylabel="Value"):
		self.channels = channels
		self.device = device
		self.startTime = None
		self.lastPoint = (0,0,0) #(systime, clocktick, val)
		self.nAvg = nAvg
		self.avgData = dict()
		self.running = True
		self.channelsOn = False
		if self.channels is None or self.channels == []:
			logger.log("No Channels to graph", self, logger.WARNING)
			return
		date = '"' + time.asctime() + '"'
		header = date + ", " + str(int(self.nAvg)) + " sample average"
		for chan in self.channels:
			self.avgData[chan.idx] = []
			sampPsec = chan.clockFreq / float(chan.value)
			header += "\n" + "CH " + str(chan.idx)  
	

		GraphFrame.__init__(self, parent, header=header,  xRange=xRange, yRange=yRange, nPoints=7000, xSize=xSize, ySize=ySize, title=title, xlabel=xlabel, ylabel=ylabel, POINTDEBUG=logger.options["debug_points"])

		# add widgets
		widgetPanel = wx.Panel(self)
		widgetSizer = wx.BoxSizer(wx.HORIZONTAL)

		self.startBtn = wx.Button( widgetPanel, wx.ID_ANY, "Start", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.sampleRateTxt = wx.StaticText(widgetPanel, wx.ID_ANY, "Sample Rate (/sec): ", wx.DefaultPosition, wx.DefaultSize, 0 ) 
		self.sampleRate = wx.TextCtrl( widgetPanel, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size( 100,-1 ), 0 )

		
		widgetSizer.Add( self.sampleRateTxt, 0, wx.TOP|wx.BOTTOM|wx.LEFT, 25 )
		widgetSizer.Add( self.sampleRate, 0, wx.BOTTOM|wx.TOP|wx.RIGHT, 20 )
		widgetSizer.Add( self.startBtn, 0, wx.TOP|wx.RIGHT, 20 )

		widgetPanel.SetSizer(widgetSizer)
		self.mainSizer.Add(widgetPanel,0, wx.EXPAND, 0)

		changeNAvg = wx.MenuItem( self.fileMenu, wx.ID_ANY, "Sample Size", "Changes size of the averaging sample", wx.ITEM_NORMAL )
		self.editMenu.AppendItem(changeNAvg)
		self.Bind( wx.EVT_MENU, self.onNAvg, id=changeNAvg.GetId() )
		self.sampleRate.Bind( wx.EVT_TEXT_ENTER, self.onRate )
		self.sampleRate.Bind( wx.EVT_KILL_FOCUS, self.onRate )
		self.startBtn.Bind( wx.EVT_BUTTON, self.onStartBtn )

		for c in self.channels:
			c.register(self)
			self.running = True
		self.updateData()
	
	
	def onStartBtn(self, event):
		if self.running:
			if self.channelsOn:
				for c in list(self.channels):
					c.stop()
				self.startBtn.Enable(False)
			else:
				for c in self.channels:
					c.start()
				self.startBtn.SetLabel("Stop")

	def onRate(self, event):
		try:
			value = float(self.sampleRate.GetValue())
		except ValueError:
			self.sampleRate.SetLabel("NaN")
		for c in self.channels:
				c.setValue(value)

	def onNAvg(self, event):

		# ask user for starting X value
		done = False
		initVal = 0
		while not done:
			initVal = wx.GetTextFromUser(message="Enter a new sample size ", caption="Sample Size", default_value="1" )
			if initVal == "":
				initVal = 1
				return
			else:
				try:
					initVal = float(initVal)
					done = True
					if initVal < 1:
						initVal = 1
				except ValueError:
					logger.message("Please enter a number", logger.WARNING)

		self.nAvg = initVal
	def onStop(self, chan, propCom):
		self.running = False
		chan.deregister(self)
		self.channels.remove(chan)
		if len(self.channels) == 0:
			self.askSave()
	def onStart(self, chan, propCom):
		if self.running:
			self.channelsOn = True
	def onSet(self, chan, propCom, wag, val):
		pass
	def onPoint(self, chan, propCom, pVal, tStamp, rTime, debugObj=None):
		if self.startTime is None:
			self.startTime = rTime
		t = rTime
		#logger.write(" (g) ch " + str(chan.idx) + " - " + str (rTime) + " = " + str(pVal))
		t = t - self.startTime
		
		self.lastPoint = (t, tStamp, pVal)
		

		self.avgData[chan.idx].append( (t, pVal) )
		if len(self.avgData[chan.idx]) >= self.nAvg:
			x=0
			y=0
			for p in self.avgData[chan.idx]:
				x += p[0]
				y += p[1]
			x = float(x) / len(self.avgData[chan.idx])
			y = float(y) / len(self.avgData[chan.idx])
			self.addPoint(x, y, chan.idx, debugObj)
			self.avgData[chan.idx] = []


	def OnClose(self, event):
		try:
			for c in self.channels:
				c.deregister(self)
		except KeyError as e:
			logger.log("Cant Deregister Graph hook. Already stopped?", self, logger.WARNING)
		if self.updateTimer is not None: self.updateTimer.cancel()
		self.Destroy()
	def askSave(self):
		if logger.ask("Save Graph Data?", logger.QUESTION):
			self.OnSave(None)

