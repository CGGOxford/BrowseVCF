#!/usr/bin/env python
import cgi
import os, sys, platform, subprocess, re
import tempfile #tempdirs and files
import shutil #deleting tempdirs and files
import urllib2 #for quote/unquote
from collections import OrderedDict
import Cookie
import xml.etree.ElementTree as ET #to parse schema XML files
import json #to read/write json
import helpers #local helper functions such as cross-platform 'wc'

#ugly hack to import from sibling, but it works
sys.path.insert(0, os.path.dirname(os.path.abspath(os.getcwd())))

#DEBUG
#sys.stderr.write('%s\n' % sys.path)

SCRIPTPATH = os.path.join(os.path.dirname(os.getcwd()), "scripts")
TEMPLOC = os.path.join(os.path.dirname(os.getcwd()), "tmp")

WIN_PLATFORM_NONFREE = False

RESULTLIMIT = helpers.RESULTLIMIT

if 'win' in platform.system().lower():
    WIN_PLATFORM_NONFREE = True

query = cgi.FieldStorage()

#filter vcfs
if "whichFilter" in query.keys():
    fname = query.getvalue('whichFilter')

    filtervals = {}

    for f in query.keys():
        if fname in f:
            filtervals[f] = query.getvalue(f)

    #retrieve the current working directory
    #and previous file if it exists
    curDir = ""
    prevExists = False
    prevFile = ""

    if 'HTTP_COOKIE' in os.environ:
        try:
            cookiestr = os.environ.get('HTTP_COOKIE')
            c = Cookie.SimpleCookie()
            c.load(cookiestr)

            curDir = urllib2.unquote(c['OGCWOrkingDir'].value)

            try:
                prevFile = urllib2.unquote(c['PrevFile'].value)
                prevExists = True
            except: #there is no previous file
                prevFile = "out000.tsv"
        except:
            pass   #fall out quietly for now

    #get values passed from Angular's $sessionStorage
    #supersedes cookies
    curDir = query.getvalue("OGCWOrkingDir")

    prevFile = query.getvalue("PrevFile")
    prevExists = True

    joinedPrevFile = None

    if prevFile is None:
        #prevFile = "out000.tsv"
        prevExists = False

    #output file should be prevFile + 1
    if prevFile is not None:
        outcount = int(prevFile[prevFile.find('0'):prevFile.find('.tsv')]) + 1
        joinedPrevFile = os.path.join(curDir, prevFile)
    else:
        outcount = 1

    outFile = ""
    if outcount < 10:
        outFile = "out00" + str(outcount) + ".tsv"
    elif outcount >= 10 and outcount < 100:
        outFile = "out0" + str(outcount) + ".tsv"
    else:
        outFile = "out" + str(outcount) + ".tsv"

    syscall = ""

    # Filter A (Filter variants according to a given field)
    if 'a' in fname:
        keep_none_variants = False
        if 'opt_a_keep_none_variants' in filtervals.keys():
            keep_none_variants = filtervals['opt_a_keep_none_variants']

        #use the API call to avoid a system call!
        from scripts.script03_filter_field import script03_api_call

        #silence output and run API filter call
        with helpers.no_console_output():
            script03_api_call(curDir, os.path.join(curDir, outFile),
                                filtervals['opt_a_field_to_filter_variants'],
                                filtervals['opt_a_operator'],
                                filtervals['opt_a_cutoff'], keep_none_variants,
                                joinedPrevFile)

    # Filter B (Filter variants according to a given field)
    elif 'b' in fname:

        smps = ""

        #Necessary hack. Angular passes this thing as a string if there's only
        #one element...how annoying
        if type(filtervals['opt_b_sample[]']) is list:
            smps = ','.join(filtervals['opt_b_sample[]'])
        else:
            smps = filtervals['opt_b_sample[]']

        #use the API call to avoid a system call!
        from scripts.script04_select_genotype import script04_api_call

        #silence output and run API filter call
        with helpers.no_console_output():
            script04_api_call(curDir, os.path.join(curDir, outFile),
                                filtervals['opt_b_genotype'], smps,
                                joinedPrevFile)


    elif 'c' in fname:

        #use the API call to avoid a system call!
        from scripts.script05_region_of_interest import script05_api_call

        #silence output and run API filter call
        with helpers.no_console_output():
            script05_api_call(curDir, os.path.join(curDir, outFile),
                                filtervals['opt_c_chromosome'],
                                filtervals['opt_c_start_pos'],
                                filtervals['opt_c_end_pos'], joinedPrevFile)

    elif 'd' in fname:

        #use the API call to avoid a system call!
        from scripts.script06_get_type import script06_api_call

        #silence output and run API filter call
        with helpers.no_console_output():
            script06_api_call(curDir, os.path.join(curDir, outFile),
                                filtervals['opt_d_variant_type'],
                                joinedPrevFile)

    elif 'e' in fname:

        genelistarr = []
        genelist = ""

        for gf in filtervals['opt_e_genelist'].split('\n'):
            curval = gf.strip()
            curval = curval.replace(',', '')

            if len(curval) > 0:
                genelistarr.append(curval)

        genelist = ','.join(genelistarr)

        negative_query = False
        if 'opt_e_negative_query' in filtervals.keys():
            negative_query = filtervals['opt_e_negative_query']

        #use the API call to avoid a system call!
        from scripts.script07_use_gene_list import script07_api_call

        #silence output and run API filter call
        with helpers.no_console_output():
            script07_api_call(curDir, os.path.join(curDir, outFile),
                                genelist, filtervals['opt_e_keyword_field'],
                                negative_query, joinedPrevFile)

    outheader = []
    outtext = []
    outtextmap = []
    outheadermap = [] #for column defs

    #get number of lines in the file using custom function
    numresults = -1

    try: #results = file line count minus header
        numresults = helpers.get_linecount(os.path.join(curDir, outFile)) - 1
    except:
        numresults = -1

    try:

        with open(os.path.join(curDir, outFile), 'r') as ifff:
            outheader = ifff.readline().strip().split('\t')

            #only store the first RESULTLIMIT results
            for i in range(0, RESULTLIMIT):
                outtext.append(ifff.readline().strip().split('\t'))

    except:
        pass #no results found

    for result in outtext:
        valmap = {}
        for i in range(0, len(result)):
             #the Bootstrap UI-Grid doesn't like full stops in the field name
             #for some reason...edit here
            valmap[outheader[i].replace('.', '_')] = result[i].strip()


        outtextmap.append(valmap)

    #Bootstrap UI-Grid doesn't like full stops in the field name for
    #some reason...edit name here
    for header in outheader:
        outheadermap.append({
            'field': header.replace('.', '_'),
            'displayName': header,
            'width': '150'
        })

    # set up data structures for output and return a JSON document
    returnvals = {}

    #change filter name from "opt_x" to "Filter x"
    fname = 'Filter ' + fname[4].upper()

    returnvals['workingdir'] = curDir
    returnvals['filtervals'] = fname
    returnvals['inputdata'] = filtervals
    returnvals['outfile'] = outFile
    returnvals['syscall'] = syscall
    returnvals['prevfile'] = outFile
    returnvals['tmpdirname'] = curDir[curDir.rfind('/')+1:]
    returnvals['outheadermap'] = outheadermap
    returnvals['outtextmap'] = outtextmap

    if numresults > RESULTLIMIT:
        returnvals['overflowFlag'] = True
    else:
        returnvals['overflowFlag'] = False

    returnvals['numresults'] = numresults

    #remove the file if we have no results
    if (returnvals['numresults'] <= 0):
        try: #remove the file if it exists
            os.remove(os.path.join(curDir, outFile))
        except:
            pass

    #print return values in JSON format
    #print """Content-type: application/json\r\n"""
    print """%s\r\n""" % json.dumps(returnvals)
