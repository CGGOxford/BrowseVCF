#!/bin/sh

export PATH=`pwd`/../python27gnu/bin:$PATH
echo $PATH

#export PYTHONPATH=`pwd`/osx_libs:$PYTHONPATH
#echo $PYTHONPATH

/usr/bin/env python --version
/usr/bin/env python launcher-cherrypy.py `pwd`/../python27gnu/bin/python 
