import wx
import wx.lib.plot
import logger
import time
import threading
import Queue

import os, sys
import graph






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
	info = graph.GraphInfoBox(window_parent,xRange=(0,100),yRange=(0,4096))
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

	



	
class NewGraphFrame( graph.GraphFrame):
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
	

		graph.GraphFrame.__init__(self, parent, header=header,  xRange=xRange, yRange=yRange, nPoints=7000, xSize=xSize, ySize=ySize, title=title, xlabel=xlabel, ylabel=ylabel, POINTDEBUG=logger.options["debug_points"])

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

