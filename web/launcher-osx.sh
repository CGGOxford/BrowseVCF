#!/bin/sh

export PATH=$CWD/../python27osx/bin:$PATH
echo $PATH

export LD_LIBRARY_PATH=$CWD/osx_libs:$LDB_LIBRARY_PATH
echo $LD_LIBRARY_PATH

python --version
python launcher-cherrypy.py
