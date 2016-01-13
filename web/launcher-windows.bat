pushd "..\WinPython-32bit-2.7.10.3\python-2.7.10"
SET PATH=%CD%;%PATH%
SET PYTHONPATH=%CD%
popd

python launcher-cherrypy.py %PYTHONPATH%\python.exe
