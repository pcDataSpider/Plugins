#import os, sys
#sys.path.append("..")

import wx
import wx.lib.plot
import time

import logger
import graph


title = "Line Scan "
description = "Line Scan"


graph_windows = []




class NewGraphFrame(graph.GraphFrame):
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



		graph.GraphFrame.__init__(self, self.window_parent, header=header, xRange=None, yRange=(0,4096), showPoints=True, xlabel="Distance", ylabel="Intensity", title="Line Scan - " + chanNames)

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
	def onHigh(self, chan, propCom, dVal):
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
		graph.GraphFrame.OnClose(self, event)


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

