#!/bin/sh

export PATH=`pwd`/../python27osx/bin:$PATH
echo $PATH

export LD_LIBRARY_PATH=`pwd`/osx_libs:$LD_LIBRARY_PATH
export PYTHONPATH=`pwd`/osx_libs:$PYTHONPATH
echo $LD_LIBRARY_PATH
echo $PYTHONPATH

python --version
python launcher-cherrypy.py
