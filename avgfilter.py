import time
import wx

import os, sys
sys.path.append("..")
import logger



title = "Average Filter"
description = "Filters noise by averaging a set number of samples together"




def run_tool(window_parent, device):
	nAvg = wx.GetNumberFromUser("Samples to average:", "Average size", "Average Filter", device.propCom.nAvg,1,100,window_parent,wx.DefaultPosition)
	if nAvg < 1:
		return
	device.setNAvg( nAvg )
	
	

