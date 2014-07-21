import wx
import logger
import Queue
import wx.lib.plot
import time
import threading
import os


title= "CEI Pulsed Experiment"
description= "Tool for pulsed experiments"


conditions = ["timerExpire", "always", "onChange", "onHigh", "onLow", "whileHigh", "whileLow"]
actions = ["setTimer", "notify", "AIStart", "AIStop"]

def run_tool(window_parent, device):
	logger.log("PulsedExperiment tool running","",logger.INFO)

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

	# ask user for trigger pins
	choices = []
	channels = []
	triggers = []
	for n in range(0,4):
		choices.append( "Digital input " + str(n) )

	dlg = wx.MultiChoiceDialog(window_parent, message="Select which pins to trigger", caption="Trigger Selection", choices=choices)
	dlg.SetSelections([0])
	if dlg.ShowModal()== wx.ID_OK:
		selection = dlg.GetSelections()
		for idx in selection:
			triggers.append( idx+4 )
	else:
		return
        dlg.Destroy() 

	mask = 0
	for pin in triggers:
		mask = mask | (1<<pin)
	device.setNAvg(1)
	device.propCom.send("resetevents")




	win = PulsedExperiment(window_parent, device, channels=plotChannels, triggers=triggers)
	win.Show()

	
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


class PulsedExperiment(GraphFrame):
	def __init__(self, parent, device, channels=None, triggers=None, rate=10000, nAvg=10, bufferSize=1):
		self.firstTime = None
		self.channels = channels
		self.device = device
		self.rate=rate
		self.nAvg=nAvg
		self.startTime = None
		self.lastPoint = (0,0,0) #(systime, clocktick, val)
		self.running = False
		self.lastTime = 0


		self.delay = 0.00001*device.propCom.CLOCKPERSEC
		self.duration = 0.00101*device.propCom.CLOCKPERSEC

		self.mask = 0
		for pin in triggers:
			self.mask = self.mask | (1<<pin)

		#self.digIdx = 0
		#self.digMask = 0
		#for ch in triggers:
		#	self.digMask = self.digMask | (1<<ch)
		#device.digitals.register(self)

		
		nPoints = bufferSize * rate
		xRange=None
		#yRange=(0,1024)
		yRange=None
		xSize=None
		ySize=None
		xlabel = "seconds"
		ylabel = "Value"
		if self.channels is None or self.channels == []:
			logger.log("No Channels to graph", self, logger.WARNING)
			return
		date = '"' + time.asctime() + '"'
		header = date + ", " + str(int(self.nAvg)) + " sample average"
		rate = rate/len(self.channels)
		for chan in self.channels:
			sampPsec = chan.clockFreq / float(chan.value)
			header += "\n" + "CH " + str(chan.idx)  
			chan.register(self)
			chan.setValue(rate)

		GraphFrame.__init__(self, parent, header=header,  xRange=xRange, yRange=yRange, nPoints=nPoints, xSize=xSize, ySize=ySize, title=title, xlabel=xlabel, ylabel=ylabel, showPoints = True,POINTDEBUG=logger.options["debug_points"])
		print "!!"
		# add widgets
		widgetPanel = wx.Panel(self)
		panelSizer = wx.BoxSizer(wx.VERTICAL)
		widgetSizer = wx.BoxSizer(wx.HORIZONTAL)
		widgetSizer2 = wx.BoxSizer(wx.HORIZONTAL)

		self.startDelayTxt = wx.StaticText( widgetPanel, wx.ID_ANY, "Delay(sec):", wx.DefaultPosition, wx.DefaultSize,0)
		self.startDelay = wx.TextCtrl( widgetPanel, wx.ID_ANY, str(self.delay/self.device.propCom.CLOCKPERSEC), wx.DefaultPosition, wx.Size(100,-1),wx.TE_PROCESS_ENTER)
		self.testDurationTxt = wx.StaticText( widgetPanel, wx.ID_ANY, "Duration(sec):", wx.DefaultPosition, wx.DefaultSize,0)
		self.testDuration = wx.TextCtrl( widgetPanel, wx.ID_ANY, str((self.duration-self.delay)/self.device.propCom.CLOCKPERSEC), wx.DefaultPosition, wx.Size(100,-1),wx.TE_PROCESS_ENTER)
		self.sampleRateTxt = wx.StaticText( widgetPanel, wx.ID_ANY, "Sample Rate(samples/sec):", wx.DefaultPosition, wx.DefaultSize,0)
		self.sampleRate = wx.TextCtrl( widgetPanel, wx.ID_ANY, str(rate), wx.DefaultPosition, wx.Size(100,-1),wx.TE_PROCESS_ENTER)
		self.stopBtn = wx.Button(widgetPanel, wx.ID_ANY, "Start", wx.DefaultPosition, wx.DefaultSize, 0)

		widgetSizer.Add(self.startDelayTxt, 0, wx.BOTTOM|wx.TOP|wx.RIGHT, 10)
		widgetSizer.Add(self.startDelay, 0, wx.BOTTOM|wx.TOP|wx.RIGHT, 10)
		widgetSizer.Add(self.testDurationTxt, 0, wx.BOTTOM|wx.TOP|wx.RIGHT, 10)
		widgetSizer.Add(self.testDuration, 0, wx.BOTTOM|wx.TOP|wx.RIGHT, 10)
		widgetSizer2.Add(self.sampleRateTxt, 0, wx.BOTTOM|wx.TOP|wx.RIGHT, 10)
		widgetSizer2.Add(self.sampleRate, 0, wx.BOTTOM|wx.TOP|wx.RIGHT, 10)
		widgetSizer2.Add(self.stopBtn, 0, wx.BOTTOM|wx.TOP|wx.RIGHT, 10)

		panelSizer.Add(widgetSizer, 0, 0, 0)
		panelSizer.Add(widgetSizer2, 0, 0, 0)
		widgetPanel.SetSizer(panelSizer)
		self.mainSizer.Add(widgetPanel,0,wx.EXPAND,0)
		self.startDelay.Bind( wx.EVT_TEXT_ENTER, self.onDelay)
		self.startDelay.Bind( wx.EVT_KILL_FOCUS, self.onDelay)
		self.testDuration.Bind( wx.EVT_TEXT_ENTER, self.onDuration)
		self.testDuration.Bind( wx.EVT_KILL_FOCUS, self.onDuration)
		self.sampleRate.Bind( wx.EVT_TEXT_ENTER, self.onRate)
		self.sampleRate.Bind( wx.EVT_KILL_FOCUS, self.onRate)
		self.stopBtn.Bind(wx.EVT_BUTTON, self.onStop)
		# bind widgets
		self.onDelay(None)
		self.onDuration(None)

		for c in self.channels:
			c.register(self)

		self.pulse = False
		self.pulseQueue = dict()
		for c in self.channels:
			self.pulseQueue[c.idx] = Queue.Queue(1000)
	def onStop(self, event):
		if self.running:
			self.stopBtn.SetLabel("Restart")
			self.running = False
			for c in self.channels:
				c.deregister(self)
			self.device.propCom.send("resetevents")
		else:
			self.stopBtn.SetLabel("Stop")
			self.data = dict()
			self.displayData = dict()
			self.firstTime = None
			self.running = True
			self.updateData()
			for c in self.channels:
				c.register(self)
			self.setEvents()
	def setEvents(self):
		# TODO switch to device.addEvent(...) and test.
		#self.device.addEvent("OnHigh", self.mask, "SetTimer", 0)
		#self.device.addEvent("OnHigh", self.mask, "SetTimer", 1)
		#self.device.addEvent("OnHigh", self.mask, "SetTimer", 2)
		self.device.setEventTimer(0, 100000)
		self.device.setEventTimer(3, 100000)
		self.device.addEvent("OnHigh", self.mask, 
					"SetTimer", 1,
					"SetTimer", 2)

		self.device.addEvent("TimerExpire", 0,
				"DOLow", 1<<1,
				"SetTimer", 3)
		self.device.addEvent("TimerExpire", 3,
				"DOHigh", 1<<1,
				"SetTimer", 0)
		self.device.addEvent("TimerExpire", 2, "AIStop", self.channels[0].idx)
		self.device.addEvent("TimerExpire", 1, "AIStart", self.channels[0].idx)
		self.device.addEvent("OnTrigger", 1, "SetTimer", 3)
		self.device.eventTrigger(1)


	def onRate(self, event):
		self.setAvg()
	def onDelay(self, event):
		self.delay = int(float(self.startDelay.GetValue())*self.device.propCom.CLOCKPERSEC)
		print "delay:" + str(self.delay)
		self.device.propCom.send("timer",[1, self.delay])
		self.setAvg()
	def onDuration(self, event):
		self.duration = self.delay + int(float(self.testDuration.GetValue())*self.device.propCom.CLOCKPERSEC)
		print "duration:" + str(self.duration)
		self.device.propCom.send("timer",[2, self.duration])
		self.setAvg()
	def setAvg(self):
		pulse = self.duration
		# calculate the total number of samples that will be taken during a single experiment
		minSamples = self.device.propCom.MAX_AVG
		for channel in self.channels:
			print("duration:" + str(self.duration) + "delay:" + str(self.delay) + "value:" + str(self.device.propCom.CLOCKPERSEC / float(self.sampleRate.GetValue())))
			samples = (self.duration-self.delay) / int(self.device.propCom.CLOCKPERSEC / float(self.sampleRate.GetValue()))
			print("samples:"+str(samples))
			samples -= 3 #leave some breathing room
			if samples > self.device.propCom.MAX_AVG:
				samples = self.device.propCom.MAX_AVG - 3
			if samples < 1:
				samples = 1
			if samples < minSamples:
				minSamples = samples

		print("minSamples=" + str(minSamples))
		rate = float(self.sampleRate.GetValue()) / minSamples
		for channel in self.channels:
			print("rate:" + str(rate))
			channel.setValue( rate )
		self.device.propCom.send("avg",  minSamples)
		

	def onPoint(self, ch, propCom, pVal, tStamp, rTime):
		if tStamp < self.lastTime:
			self.lastTime -= (1<<32)-1
		if tStamp - self.lastTime > float(self.duration):
			self.pulseExpire()
		self.lastTime = tStamp

		self.pulseQueue[ch.idx].put( (rTime,pVal) )
		if self.pulse:
			self.pulseTimer.cancel()
		self.pulse = True
		def update():
			self.pulse = False
			print("Expire!")
			self.pulseExpire()
		self.pulseTimer = threading.Timer(.5 + (float(self.duration)/self.device.propCom.CLOCKPERSEC),update)
		self.pulseTimer.start()
	def pulseExpire(self):
		for channel in self.channels:
			v=0
			rTime = 0
			i=0
			while not (self.pulseQueue[channel.idx].empty()):
				rTime,pVal = self.pulseQueue[channel.idx].get()
				v = v + pVal
				i+=1
			if i>0:
				v/=i
				if self.firstTime is None:
					self.firstTime = rTime
				rTime = rTime - self.firstTime
				self.addPoint( rTime,v,channel.idx)

	def OnClose(self,event):
		if self.running:
			self.onStop(None)
			for c in self.channels:
				c.deregister(self)
		self.OnSave(None)
		GraphFrame.OnClose(self,event)
		





colorTable = [ "blue", "red", "green", "yellow", "purple", "black" ]


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
	

	


