#!/usr/bin/env python
import cgi
import os, sys, platform, subprocess
import tempfile #tempdirs and files
import shutil #deleting tempdirs and files
import helpers #helpful functions
import multiprocessing #to get core counts and display them to user

import Cookie
import xml.etree.ElementTree as ET #to parse schema XML files
import json #to read/write json

#ugly hack to import from sibling, but it works
sys.path.insert(0, os.path.abspath(os.getcwd()))

#DEBUG
sys.stderr.write('%s\n' % sys.path)

#use the API call to avoid a system call!
from scripts.script01_preprocess import script01_api_call

SCRIPTPATH = os.path.join(os.getcwd(), "scripts")
TEMPLOC = os.path.join(os.getcwd(), "tmp")

WIN_PLATFORM_NONFREE = False

if 'win' in platform.system().lower():
    WIN_PLATFORM_NONFREE = True
    TEMPLOC = os.getcwd() + "\\tmp\\"

query = cgi.FieldStorage()

if "processVCF" in query.keys():
    fname = query.getvalue('processVCF')

    curDir = tempfile.mkdtemp(dir = TEMPLOC)
    if WIN_PLATFORM_NONFREE:
        curDir = curDir.replace('\\', '\\\\')

    #print header
    print """Content-type: application/json\r\n"""

    #run the API call for preprocessing
    with helpers.no_console_output():
        (availsamples, NOFILTERB) = script01_api_call(fname, curDir)

    #collect output
    myfields2 = {}
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
    nCores = multiprocessing.cpu_count() - 1

    if nCores < 1:
        nCores = 1

    myfields2['numCores'] = nCores

    #the final return dictionary, JSONified
    availfields_str = json.dumps(myfields2, encoding="utf-8")

    #write out the JSON response
    print """%s""" % availfields_str
