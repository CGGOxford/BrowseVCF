#!/usr/bin/env python
import cgi
import os, sys, platform, subprocess, re, shutil
import tempfile #tempdirs and files
import shutil #deleting tempdirs and files
import urllib2 #for quote/unquote
from collections import OrderedDict
import Cookie
import xml.etree.ElementTree as ET #to parse schema XML files
import json #to read/write json

import helpers #local helper functions such as cross-platform line count

RESULTLIMIT = helpers.RESULTLIMIT

query = cgi.FieldStorage()

if 'remFilename' in query.keys():

    returnvals = {}

    curDir = query.getvalue('workingdir')
    prevFile = query.getvalue('remFilename')

    outFile = ""

    #remove this file here
    #TODO: Check if this will work on Windows
    os.remove('%s/%s' % (query.getvalue('workingdir'), prevFile))

    outcount = int(prevFile[prevFile.find('0'):prevFile.find('.tsv')]) - 1

    if outcount >= 0:
        if outcount < 10:
            outFile = "out00" + str(outcount) + ".tsv"
        elif outcount >= 10 and outcount < 100:
            outFile = "out0" + str(outcount) + ".tsv"
        else:
            outFile = "out" + str(outcount) + ".tsv"


    #read the new (old) results file and return the data
    #parse out the data from the output file and return it in JSON
    #format changed as of tag v0.5 to export this as a map/dict
    #which is the easiest way for angular to produce a sortable table
    outheader = []
    outtext = []
    outtextmap = []
    outheadermap = [] #for column defs

    #get number of lines in the file using custom function
    numresults = -1

    try:
        #result count = file line count minus header
        numresults = helpers.get_linecount('%s/%s' % (curDir, outFile)) - 1
    except:
        numresults = -1

    try:
        with open('%s/%s' % (curDir, outFile), 'r') as ifff:
            outheader = ifff.readline().strip().split('\t')

            #only store the first RESULTLIMIT results
            for i in range(0, RESULTLIMIT):
                outtext.append(ifff.readline().strip().split('\t'))

    except:
        pass #no results found


    for result in outtext:
        valmap = {}
        for i in range(0, len(result)):
            #Bootstrap UI-Grid doesn't like full stops in the field name
            #for some reason...edit here
            valmap[outheader[i].replace('.', '_')] = result[i].strip()

        outtextmap.append(valmap)

    #Bootstrap UI-Grid doesn't like full stops in the field name
    #for some reason...edit here
    for header in outheader:
        outheadermap.append({
            'field': header.replace('.', '_'),
            'displayName': header,
            'width': '150'
        })


    returnvals['outheadermap'] = outheadermap

    if numresults > RESULTLIMIT:
        returnvals['overflowFlag'] = True
    else:
        returnvals['overflowFlag'] = False

    returnvals['numresults'] = numresults

    #working directory and the name of the file that was removed
    returnvals['workingdir'] = curDir
    returnvals['removedfile'] = prevFile

    #use this flag to determine whether the output file is "out000.tsv"
    #we need to remove the sessionStorage for PrevFile so that this doesn't get
    #passed in as a -p parameter to Silvia's scripts
    if outcount == 0:
        returnvals['rewindedToBeginning'] = True
        outFile = None
    else:
        returnvals['rewindedToBeginning'] = False

    returnvals['newPrevFile'] = outFile

    #return JSON-formatted output
    #print '''Content-type: application/json\r\n'''
    print '''%s\r\n''' % json.dumps(returnvals)
