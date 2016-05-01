#!/bin/sh

export PATH=`pwd`/../python27osx/bin:$PATH
echo $PATH

#export PYTHONPATH=`pwd`/osx_libs:$PYTHONPATH
#echo $PYTHONPATH

/usr/bin/env python --version
/usr/bin/env python launcher-cherrypy.py `pwd`/../python27osx/bin/python 
