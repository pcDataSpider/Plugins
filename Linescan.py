#import os, sys
#sys.path.append("..")

import wx
import wx.lib.plot
import time

import logger
#import graph

import threading
import Queue
import os, sys

title = "Line Scan "
description = "Line Scan"


graph_windows = []



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

		if debugObj is not None:
			self.data[idx].append((x,y,debugObj))
		else:
			self.data[idx].append((x,y))
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
	

	





class NewGraphFrame(GraphFrame):
	recording = False	# True if hooks are capturing data, False if idle
	samples = dict()	# sample data
	graphPlot = None 	# window handle
	pointFuncID = 0		# point handler ID#
	pushFuncID = 0		# push handler ID#
	nTest = 0 		# number of tests performed so far * inc

	def __init__(self, window_parent, device, sample_size, initVal, inc, started_channels, triggerPin):
		self.samples = dict()
		self.window_parent = window_parent
		self.device = device
		self.sample_size = sample_size
		self.initVal = initVal
		self.inc = inc
		self.started_channels = started_channels
		self.audible = True   # True to indicate sample end with an audible tone
		self.recording = True # true when this window has "focus" of the device
		self.sampling = False # only True after push button
		self.nTest = self.initVal
		self.digIdx = triggerPin
		self.digMask = 1 << self.digIdx


		if len(started_channels) > 1:
			chanNames = "Analogs "
		else:
			chanNames = "Analog "
		for c in started_channels[:-1]:
			chanNames += str(c.idx) + ", "
		chanNames += str(started_channels[-1].idx) 

		date = '"' + time.asctime() + '"'
		header = date + ", " + str(int(self.sample_size)) + " sample average"
		for chan in self.started_channels:
			sampPsec = chan.clockFreq / float(chan.value)
			header += "\n" + "CH " + str(chan.idx) + ", " + str(sampPsec) + " samples per second" 



		GraphFrame.__init__(self, self.window_parent, header=header, xRange=None, yRange=(0,4096), showPoints=True, xlabel="Distance", ylabel="Intensity", title="Line Scan - " + chanNames)

		self.toggleSound = wx.MenuItem( self.fileMenu, wx.ID_ANY, "Turn sound off", "makes a sound after a sample is finished", wx.ITEM_NORMAL )
		self.editMenu.AppendItem(self.toggleSound)
		self.Bind( wx.EVT_MENU, self.OnSound, id=self.toggleSound.GetId() )
		self.lastpoint = (self.initVal, 0)
		self.updateData()

		
		def pushHandler(propCom):
			self.startSample(propCom)



		self.pushFuncID = self.device.propCom.register("push", pushHandler)
		self.device.digitals.register(self)
		for chan in self.started_channels:
			chan.register(self) 
		logger.log("line scan started" , "")
	def onHigh(self, chan, propCom, dVal, rTime):
		self.startSample(propCom)
	def onPoint(self, chan, propCom, pVal, tStamp, rTime, debugObj=None):
		if not self.sampling:
			return

		try:
			if chan.idx not in self.samples:
				logger.log("new plotting channel " , str(chan.idx), logger.INFO)
				self.samples[chan.idx] = [[],0]

			# limit num of samples
			if self.samples[chan.idx][1] < self.sample_size:
				self.samples[chan.idx][0].append( pVal )
				self.samples[chan.idx][1] += 1
			else:
				# test if any inputs are waiting
				end = True
				for i in self.samples:
					if self.samples[i][1] < self.sample_size:
						end = False
				if end:
					self.endSample()
		except ValueError as e:
			logger.log("Incorrect values to 'p'", e, logger.WARNING)
		except TypeError as e:
			logger.log("Incorrect types to 'p'", e, logger.WARNING)

	def stop(self):
		if self.recording:
			try:
				self.device.propCom.deregister("push",self.pushFuncID)
				self.device.digitals.deregister(self)
				for chan in self.started_channels:
					chan.deregister(self)
			except KeyError as e:
				logger.log("Cant deregister hooks", str(self.pointFuncID) + "+" + str(self.pushFuncID), logger.ERROR)
		self.recording = False
		
	def restart(self):
		pass

	def startSample(self, propCom):
		self.sampling = True
		for idx in self.samples:
			self.samples[idx] = [[],0]
		for chan in self.started_channels:
			chan.start()
		#propCom.send("start",self.channel_mask)
	def endSample(self):
		logger.log( "Sample Period Over", 0, logger.INFO)
		self.sampling = False
		for chan in self.started_channels:
			chan.stop()
		# take average of all samples and plot
		avg = dict()
		if self.samples:
			for idx in self.samples:
				if self.samples[idx][1] == 0:
					avg[idx] = 0
					logger.log("no samples recieved", idx, logger.ERROR)
				else:
					total = 0
					n = 0
					t = time.time()
					print self.samples[idx]
					for d in self.samples[idx][0]:
						total += d
						n += 1
					print "average = " + str(total) + "/" + str(n) 
					total = total / n
					print "average = " + str(total)
					
					avg[idx] = total
					self.samples[idx] = [[],0]
				logger.write("LineScan:" + "addPoint " + str(self.nTest) + "," + str(avg[idx]) + "," + str(idx))
				self.addPoint(self.nTest, avg[idx], idx)
			#if self.outFile is not None:
			#	try:
			#		self.outFile.write(str(avg[self.main_input]) + "\n")
			#	except ValueError as e:
			#		logger.log("Error writing to file", e, logger.WARNING)

				
		else:
			logger.log("No samples recieved", " ", logger.ERROR)
		if self.audible:
			wx.Bell()
		self.nTest += self.inc

	def OnSave2(self,event):
		filetypes = "CSV files (*.csv)|*.csv|Text files (*.txt)|*.txt|All files|*"
		dlg = wx.FileDialog(self, "Choose a file", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT, wildcard=filetypes)
		outFile = None
		if dlg.ShowModal()==wx.ID_OK:
			try:
				filename=dlg.GetFilename()
				dirname=dlg.GetDirectory()
				fullPath = os.path.join(dirname, filename)
				date = '"' + time.asctime() + '"'
				self.SetTitle( self.title + " - " + filename )
				outFile = open(fullPath, "w")
				# write header info
				outFile.write( date )
				for idx in self.data:
					outFile.write("," + str(idx) )
				outFile.write( "\n" )
				# write data
				nData = 0
				for idx in self.data:
					if len(self.data[idx]) > nData:
						nData = len( self.data[idx] )
				xList = []
				x = self.initVal
				for n in range( nData ):
					xList.append((n, x))
					x += self.inc
				for n, x in sorted(xList):
					outFile.write( str(x) + "," )
					for idx in self.data:
						try:
							outFile.write( str(self.data[idx][n][1]) )
						except IndexError:
							pass
						outFile.write( "," )

					outFile.write( "\n")
				outFile.close()
			except IOError as e:
				logger.log("Error opening file", e, logger.WARNING)
				logger.message("Error opening file.", logger.ERROR)
			except ValueError as e:
				logger.log("Error writing file", e, logger.WARNING)
				logger.message("Error writing file.", logger.ERROR)
		dlg.Destroy()
	def OnSound(self, event):
		if self.audible:
			self.audible = False
			self.toggleSound.SetItemLabel("Turn sound on")
		else:
			self.audible = True
			self.toggleSound.SetItemLabel("Turn sound off")
			
	def OnClose(self,event):
		global graph_windows
		self.stop()
		graph_windows.remove(self)
		GraphFrame.OnClose(self, event)


def run_tool(window_parent, device):
	global graph_windows

	# ask user for input selection
	i = 0
	choices = []
	#for c in device.analogIn:
	for key, c in device.analogIn.iteritems():
		choices.append( "Analog input " + str(c.idx) )
	dlg = wx.MultiChoiceDialog(window_parent, message="Select which inputs to sample", caption="Input Selection", choices=choices)
	dlg.SetSelections([0])
 
 	started_channels = []
	if dlg.ShowModal()== wx.ID_OK:
		selection = dlg.GetSelections()
		for idx in selection:
			started_channels.append(device.channels[idx])
		if len(selection) <= 0:
			logger.log("No inputs selected", "nothing to average", logger.INFO)
	else:
		return
	
        dlg.Destroy()


	# ask user for input selection for trigger
	i = 0
	choices = []
	for n in range(4):
		choices.append( "Digital input " + str(n) )
	dlg = wx.SingleChoiceDialog(window_parent, message="Select input trigger", caption="Trigger Selection", choices=choices)
	dlg.SetSelection(0)
 
 	triggerPin = 0
	if dlg.ShowModal()== wx.ID_OK:
		triggerPin = dlg.GetSelection() + 4
	else:
		return
        dlg.Destroy()

	# ask user for starting X value
	done = False
	initVal = 0
	while not done:
		initVal = wx.GetTextFromUser(message="Enter the initial X axis value ", caption="Initial Value", default_value="0" )
		if initVal == "":
			initVal = 0
			return
		else:
			try:
				initVal = float(initVal)
				done = True
			except ValueError:
				logger.message("Please enter a number", logger.WARNING)

	# ask user for increment size
	done = False
	inc = 0
	while not done:
		inc = wx.GetTextFromUser(message="Enter a number for the sample step", caption="Sample Step", default_value="10" )
		if inc == "":
			inc = 0
			return
		else:
			try:
				inc = float(inc)
				done = True
			except ValueError:
				logger.message("Please enter a number", logger.WARNING)

				done = False
	# ask user for sample size
	done = False
	sample_size = 0
	while not done:
		sample_size = wx.GetTextFromUser(message="Enter the number of samples to be averaged", caption="Sample Size", default_value="100" )
		if sample_size == "":
			return
		else:
			try:
				sample_size = float(sample_size)
				done = True
			except ValueError:
				logger.message("Please enter a number", logger.WARNING)
	# ask user for increment size
	#inc = wx.GetTextFromUser(message="Enter an integer for the sample step (Integers Only)", caption="Sampling Step", value=10 )
	#if inc == "":
	#	inc = 1
	#	return

	# ask user for sample time
	#sample_size = wx.GetTextFromUser(message="Enter the number of samples to be averaged", caption="Sample Size", value=100 )
	#if sample_size == "":
	#	sample_size = 1
	#	return


	# disable any active windows
	for w in graph_windows:
		if w.recording:
			w.stop()


	window = NewGraphFrame(window_parent, device, sample_size, initVal, inc, started_channels, triggerPin)
	window.Show()
	graph_windows.append(window)

