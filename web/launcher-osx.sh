#!/bin/sh

export PATH=`pwd`/../python27osx/bin:$PATH
echo $PATH

export LD_LIBRARY_PATH=`pwd`/osx_libs:$LDB_LIBRARY_PATH
echo $LD_LIBRARY_PATH

python --version
python launcher-cherrypy.py
