#!/usr/bin/env python
import cgi
import psutil #to get proper cpu counts with CherryPy
import os, sys, platform, subprocess
import tempfile #tempdirs and files
import shutil #deleting tempdirs and files
import urllib2 #for quote/unquote
import helpers #helpful functions
import Cookie
import xml.etree.ElementTree as ET #to parse schema XML files
import json #to read/write json

import multiprocessing #manage cores

#ugly hack to import from sibling, but it works
ROOTPATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOTPATH)

#use the API call to avoid a system call!
from scripts.script02_convert_to_wt import script02_api_call
from scripts.script02_convert_to_wt import get_total_variant_count

SCRIPTPATH = os.path.join(os.path.dirname(os.getcwd()), "scripts")
TEMPLOC = os.path.join(ROOTPATH, "tmp")

WIN_PLATFORM_NONFREE = False

if 'win' in platform.system().lower():
    WIN_PLATFORM_NONFREE = True

query = cgi.FieldStorage()

if "selval[]" in query.keys():
    ifields = query.getvalue('selval[]')

    inputfields = ""

    if type(ifields) is list and len(ifields) > 1:
        inputfields = ','.join(ifields)
    else:
        inputfields = ifields
        mfields = []
        mfields.append(ifields)
        ifields = mfields #move it into an array for return value purposes

    numCores = '1'

    try:
        numCores = query.getvalue('numCores')
        if numCores is None or numCores == '':
            numCores = 1

        nCores = psutil.NUM_CPUS 

        if numCores >= str(nCores) or numCores == '0':
            numCores = str(nCores - 1)
    except:
        pass

    #retrieve the current working directory
    #TODO: Remove the cookie block once it's confirmed safe to do so
    curDir = ""
    if 'HTTP_COOKIE' in os.environ:
        try:
            cookiestr = os.environ.get('HTTP_COOKIE')
            c = Cookie.SimpleCookie()
            c.load(cookiestr)

            curDir = urllib2.unquote(c['OGCWOrkingDir'].value)
        except:
            pass  #fall out quietly for now

    #get values passed from Angular's $sessionStorage
    #supersedes cookies
    curDir = query.getvalue('OGCWOrkingDir')

    #TODO: os.path.join() this
    if WIN_PLATFORM_NONFREE:
        curDir = curDir.replace('\\', '\\\\')

    #default input file created by script 1 in the previous step (vcfload.py)
    inpfile = 'pre_processed_inp_file.vcf.gz'

    #suppress output, if any, and run API call
    with helpers.no_console_output():
        script02_api_call(os.path.join(curDir, inpfile),
                                    curDir, inputfields, numCores)

    #append the latest indexed fields to our parsed-fields tracker file
    with open('%s/indexedfields.txt' % curDir, 'a') as offf:
        for f in ifields:
            offf.write('%s\n' % f)

    #read the fields back in for json return value
    retfields = []
    availSamples = [] #populate if a GT wormtable is created for the sample
    with open('%s/indexedfields.txt' % curDir, 'r') as ifff:
        for line in ifff:
            lne = line.strip()
            if lne not in retfields:
                retfields.append(lne)

            if ".GT" in lne and lne[:lne.find('.GT')] not in availSamples:
                availSamples.append(lne[:lne.find('.GT')])

    returnvals = {}
    returnvals['workingdir'] = curDir
    returnvals['indexedfields'] = retfields
    returnvals['availsamples_filterb'] = availSamples

    #get total count with wormtable helper function in script 2
    returnvals['totalvariants'] = get_total_variant_count(curDir)

    if len(availSamples) < 1:
        returnvals['nofilterb'] = True
    else:
        returnvals['nofilterb'] = False

    jsonreturn = json.dumps(returnvals)

    #print out the JSON return value
    #print """Content-type: application/json\r\n"""
    print """%s\r\n""" % jsonreturn
