#!/usr/bin/env python
import cgi
import psutil #to get proper cpu counts with CherryPy
import os, sys, platform, subprocess
import tempfile #tempdirs and files
import shutil #deleting tempdirs and files
import helpers #helpful functions
import multiprocessing #to get core counts and display them to user

import Cookie
import xml.etree.ElementTree as ET #to parse schema XML files
import json #to read/write json

import cherrypy

#ugly hack to import from sibling, but it works
ROOTPATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOTPATH)

#DEBUG
#sys.stderr.write('%s\n' % sys.path)

#use the API call to avoid a system call!
from scripts.script01_preprocess import script01_api_call

SCRIPTPATH = os.path.join(os.path.dirname(os.getcwd()), "scripts")
TEMPLOC = os.path.join(ROOTPATH, "tmp")

WIN_PLATFORM_NONFREE = False

if 'win' in platform.system().lower():
    WIN_PLATFORM_NONFREE = True

query = cgi.FieldStorage()

if "processVCF" in query.keys():
    fname = query.getvalue('processVCF')

    curDir = tempfile.mkdtemp(dir = TEMPLOC)
    if WIN_PLATFORM_NONFREE:
        curDir = curDir.replace('\\', '\\\\')

    #collect output
    myfields2 = {}

    #run the API call for preprocessing
    with helpers.no_console_output():
        try:
            (availsamples, NOFILTERB) = script01_api_call(fname, curDir)
        except Exception, e: #catch all
            myfields2['ERRMSG'] = str(e)


    myfields2['ostuff'] = ""
    myfields2['nofilterb'] = NOFILTERB #by default, filter B will be enabled

    # In preparation for step 2, load the schema for fields that can be parsed
    tree = ET.parse('%s/schema.xml' % curDir)
    root = tree.getroot()
    myfields = []
    for fname in root.iter('column'):
        if fname.attrib['name'] != 'row_id': #don't include row_id
            myfields.append(
                {
                    'fname': fname.attrib['name'].strip(),
                    'fdesc': fname.attrib['description'].strip()
                })

    myfields2['filterfields'] = myfields
    myfields2['workingdir'] = curDir
    myfields2['downloadpath'] = curDir[curDir.find('tmp'):].replace('\\\\', '/')
    myfields2['availsamples'] = availsamples

    #return number of cores on system minus one
    nCores = 1

    try:
    	nCores = int(psutil.cpu_count()) - 1
    except:
    	nCores = int(psutil.NUM_CPUS) - 1

    if nCores < 1:
        nCores = 1

    myfields2['numCores'] = nCores

    if ('ERRMSG' not in myfields2.keys()):
        myfields2['ERRMSG'] = "None"

    #the final return dictionary, JSONified
    availfields_str = json.dumps(myfields2, encoding="utf-8")

    #write out the JSON response
    #print """Content-type: application/json\r\n"""

    #HOTFIX: The '\n' before the response is required for Chromium/Chrome
    #on Windows, and possibly Safari on Mac
    print """\n%s""" % availfields_str
