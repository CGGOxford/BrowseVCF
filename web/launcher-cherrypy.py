#!/usr/bin/env python
#Launches CherryPy web server, and browser with correct URL

import os, sys
import cherrypy
import cpcgiserver
import webbrowser
import thread
import multiprocessing
import psutil #when multiprocessing doesn't work on CherryPy
import threading
import time
import Tkinter as tk #GUI stuff
import tkFileDialog #file open dialog
import json #to serialise js config

import socket #to find an open port

VCFFILENAME = '' #set by the open dialog

VCFSTORAGEFILE = os.path.join(os.getcwd(), "js/vcfHistory.json")

HOSTNAME = '127.0.0.1'

#seed a port number in case random portnum search doesn't work
PORTNUM = 27013

myconfig = {

    "global": {
        # Server settings
        "server.socket_host": "127.0.0.1",
        "server.socket_port": PORTNUM,
        "engine.timeout_monitor.on": False,
        "response.timeout": 15000000
    },
    "/":{
        "tools.staticdir.on": True,
        "tools.staticdir.dir": os.getcwd(),
        "tools.staticdir.index": 'index.html',
        "response.timeout": 15000000
    },
    "/cgi-bin": {
        # Enable CgiServer
        "tools.cgiserver.on": True,
        # Directory with Python-CGI files
        "tools.cgiserver.dir": os.path.join(os.getcwd(), "cgi-bin"),
        # URL for directory with Python-CGI files
        "tools.cgiserver.base_url": "/cgi-bin",
        # Connect Python extension with Python interpreter program
        "tools.cgiserver.handlers": {".py": "python"},
        "response.timeout": 15000000
    }

}


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
        try:
            with open(VCFSTORAGEFILE, 'r') as jsonfile:
                curfiles = json.load(jsonfile)
        except: #vcfHistory.json doesn't exist, or something else went wrong
            curfiles = []

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
        webbrowser.open_new('http://%s:%d' % (HOSTNAME,PORTNUM))

        return fname

    def createWidgets(self):
        self.chooseFileButton = tk.Button(self, text='Choose a VCF file', command=self.chooseFile)
        self.quitButton = tk.Button(self, text='Quit Application', command=self.quit)
        self.chooseFileButton.grid()
        self.quitButton.grid()


class ServeThread(threading.Thread):

    global myconfig

    def __init__(self, portnum = PORTNUM):

        myconfig['global']['server.socket_port'] = portnum
        threading.Thread.__init__(self)

    def run(self):
    	print "PROCS: %s" % os.environ.get('NUMBER_OF_PROCESSORS')
        app = cherrypy.Application(None, config=myconfig)
        cherrypy.quickstart(app, config=myconfig)
        cherrypy.engine.block()

#solution for getting an available port
#adapted from: http://unix.stackexchange.com/a/132524
def get_open_port():

    s = socket.socket()
    s.bind(("", 0))
    portnum = int(s.getsockname()[1])
    s.close()

    return portnum

def main():

    global PORTNUM
    global myconfig

    try:
        PORTNUM = get_open_port()
    except:
        pass

    print "ARGS: %s" % (sys.argv,)

    if len(sys.argv) >= 2:
    	myconfig['/cgi-bin']['tools.cgiserver.handlers'] = { '.py': sys.argv[-1] }
	sys.stderr.write('BROWSEVCF CONFIGURATION\n%s\n' % sys.argv[-1])

    s = ServeThread(portnum = PORTNUM)
    s.daemon = True
    s.start()

    app = GUIApp()

    app.master.title('BrowseVCF Control Panel')

    #while True:
    #    time.sleep(1)

    #load the window
    app.mainloop()


if __name__ == '__main__':

    main()
