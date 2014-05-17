import time
import wx

import os, sys
sys.path.append("..")
import logger



title = "Speed Test"
description = "Tests the transmission speed of the device"

data = []
start_time = 0



def run_tool(window_parent, device):
	global data
	global start_time
	data = []
	nData = 0
	start_time = time.time()



	

	# wait some time
	dlg = WaitingMessage(window_parent, device)
	dlg.Show()

def stat():
	"""calculates information about data connection"""
	if data == []:
		wx.MessageBox("No samples recorded", "No Data", wx.OK | wx.ICON_EXCLAMATION)
		return
	# find total samples/sec
	first = data[0]
	last = data[-1]
	dT = last - first
	total_dT = time.time() - start_time
	samp_per_sec = len(data)/dT
	# find time between samples
	dT_list = []
	for i in range( len(data)-1 ):
		dT_list.append( data[i+1] - data[i] )	
	total = 0
	min_dT = 999999
	max_dT = 0
	for p in dT_list:
		total += p
		if p > max_dT:
			max_dT = p
		elif p < min_dT:
			min_dT = p
	avg_time = total / len(dT_list)

	message = "Results: \n\tAverage Samples per Second: " + str(samp_per_sec) + "\n\tAverage time between samples: " + str(avg_time) + " seconds\n\ttotal samples taken: " + str(len(data)) + "\n\ttime elapsed between samples: " + str(dT) + "\n\ttotal elapsed time: " + str(total_dT)
	wx.MessageBox(message, "Results", wx.OK | wx.ICON_INFORMATION)




class WaitingMessage(wx.Dialog):
	def __init__(self, parent, device):
		self.device = device
		wx.Dialog.__init__( self, parent, id = wx.ID_ANY, title = "Waiting..."  )
		ico = wx.Icon('OFSI-Logo.ico', wx.BITMAP_TYPE_ICO )
		self.SetIcon( ico )

		bSizer = wx.BoxSizer( wx.VERTICAL )
		bSizer.AddSpacer( ( 0, 10), 0, wx.EXPAND, 5 )
		txt2 = wx.StaticText( self, wx.ID_ANY, "Start collecting data.\nClose this box when enough data has been collected", wx.DefaultPosition, wx.DefaultSize, 0 )
		bSizer.Add( txt2, 0, wx.LEFT|wx.TOP, 10 )
		self.SetSizer( bSizer )
		self.Layout()
		self.Fit()
		
		self.Centre( wx.BOTH )


		for x in self.device.analogIn:
			ch = self.device.channels[x]
			ch.register(self)

		self.Bind( wx.EVT_CLOSE, self.onClose)

	def onPoint(self,propCom, idx, cIdx, *args):
		data.append(time.time())
	def onClose(self, event):
		try:
			for x in self.device.analogIn:
				ch = self.device.channels[x]
				ch.deregister(self)
		except KeyError as e:
			logger.log("Can't deregister stat hook", pointFuncID)
		stat()
		self.Destroy()
