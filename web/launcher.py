#!/usr/bin/env python
#Launches web server, and browser with correct URL

import os, sys
import BaseHTTPServer
import CGIHTTPServer
import webbrowser
import thread
import threading
import time
import Tkinter as tk #GUI stuff
import tkFileDialog #file open dialog
import json #to serialise js config

import socket #to find an open port

VCFFILENAME = '' #set by the open dialog

VCFSTORAGEFILE = os.path.join(os.getcwd(), "js/vcfHistory.json")

PORTNUM = 27013

class GUIApp(tk.Frame):
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)

        self.file_opt = options = {}
        options['defaultextension'] = '.vcf.gz'
        options['filetypes'] = [('Compressed VCF files', '.vcf.gz'), ('VCF files', '.vcf'), ('all files', '.*')]
        options['initialdir'] = os.getcwd()
        options['parent'] = master
        options['title'] = 'Choose a VCF(.gz) file to analyse'

        self.grid()
        self.createWidgets()

    def chooseFile(self):
        fname = tkFileDialog.askopenfilename(**self.file_opt)
        VCFFILENAME = fname
        sys.stderr.write('Chosen %s\n' % VCFFILENAME)

        curfiles = []
        with open(VCFSTORAGEFILE, 'r') as jsonfile:
            curfiles = json.load(jsonfile)

        myval = {"name": VCFFILENAME}

        if myval in curfiles:
            curfiles.remove(myval)

        #keep the most recent file as the last value, which will auto-populate the list
        curfiles.append(myval)


        #restrict to 10 entries
        if len(curfiles) > 10:
            curfiles.pop(0) #remove first entry

        #write the file
        with open(VCFSTORAGEFILE, 'w') as jsonfile:
            json.dump(curfiles, jsonfile, indent=4, sort_keys=True)

        #open the browser
        #webbrowser.get('firefox').open_new('http://localhost:8000')
        webbrowser.open_new('http://localhost:%d' % (PORTNUM,))

        return fname

    def createWidgets(self):
        self.chooseFileButton = tk.Button(self, text='Choose a VCF file', command=self.chooseFile)
        self.quitButton = tk.Button(self, text='Quit Application', command=self.quit)
        self.chooseFileButton.grid()
        self.quitButton.grid()


class ServeThread(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        httpd = BaseHTTPServer.HTTPServer(('localhost', PORTNUM), CGIHTTPServer.CGIHTTPRequestHandler)
        httpd.serve_forever()

#solution for getting an available port
#adapted from: http://unix.stackexchange.com/a/132524
def get_open_port():

    s = socket.socket()
    s.bind(("", 0))
    portnum = int(s.getsockname()[1])
    s.close()

    return portnum

if __name__ == '__main__':

    try:
        PORTNUM = get_open_port()
    except:
        pass

    s = ServeThread()
    s.daemon = True
    s.start()

    app = GUIApp()

    app.master.title('BrowseVCF Control Panel')


    #while True:
    #    time.sleep(1)

    #load the window
    app.mainloop()
