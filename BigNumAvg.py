import Queue
import threading
import random
import wx
import wx.lib.scrolledpanel as scrolled
import logger



title = "Billboard"
description = "Displays a large billboard to display the average value for a channel"

def run_tool(window_parent, device):
	availIdx = []
	availChoice = []
	for idx in device.analogIn:
		availIdx.append(device.channels[idx])
		availChoice.append("Analog Input " + str(idx))
	chan = wx.GetSingleChoiceIndex("Select which input to display", "Input", availChoice, window_parent)
	chan = availIdx[chan]
	billboard = BillboardDialog(window_parent, device, 1, chan)
	billboard.Show()

class BillboardDialog(wx.Frame):

	
	def __init__(self, window_parent, device, sample_size, chan):
		self.device = device
		self.chan = chan
		self.timer = None
		self.sample_size = sample_size
		wx.Frame.__init__(self, window_parent, wx.ID_ANY, "BillBoard - " + str(chan.name))
		ico = wx.Icon('OFSI-Logo.ico', wx.BITMAP_TYPE_ICO )
		self.SetIcon( ico )
	
		#self.SetDoubleBuffered(True)
		#self.SetDoubleBuffered(False)
		
		mainSizer = wx.BoxSizer( wx.VERTICAL )
		panelSizer = wx.BoxSizer( wx.HORIZONTAL )
		self.font = wx.Font(200, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)

	
		panel = wx.Panel(self)
		initVal = "0000.0"
		if sample_size == 1:
			initVal = "0000"
		self.txtValue = wx.StaticText(self, label=initVal)
		self.txtValue.SetFont(self.font)
		self.gaugeMeter = wx.Gauge( self, wx.ID_ANY, 4096, wx.DefaultPosition, wx.Size( 75,-1 ), wx.GA_VERTICAL|wx.GA_SMOOTH )

		panelSizer.Add(self.txtValue, 0, wx.ALL, 20)
		panelSizer.Add((0,0),1)
		panelSizer.Add(self.gaugeMeter, 0, wx.ALL|wx.EXPAND, 5)
		panel.SetSizer(panelSizer)
		mainSizer.Add(panel, 1, wx.ALL|wx.EXPAND)
		self.SetSizer(mainSizer)
		self.Fit()

		self.samples = Queue.Queue(sample_size)
		self.total = 0
		self.nSamples = 0
		
		chan.register(self)
		self.Bind( wx.EVT_CLOSE, self.OnClose )


	def onPoint(self, chan, propCom, pVal, tStamp, rTime, debugObj=None):
		self.add(pVal)
	def add(self, value):
		if self.samples.full():
			self.nSamples = self.sample_size
			self.total-=self.samples.get()
		else:
			self.nSamples += 1
		self.samples.put(value)
		self.total+=value



		self.label = "{0:06.1f}".format( float(self.total)/self.nSamples)
		if self.sample_size == 1:
			self.label = "{0:04}".format( self.total )
		self.gaugeMeter.SetValue(value)
		if self.timer is None:
			self.timer = threading.Timer(0.2,self.update)
			self.timer.start()
	def update(self):
		self.txtValue.SetLabel(self.label)
		self.timer = None
	
	def OnClose(self, event):
		try:
			self.chan.deregister(self)
		except KeyError as e:
			logger.log("Can't deregister billboard hook", self)
		self.Destroy()


