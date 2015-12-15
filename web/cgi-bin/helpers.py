#!python
## Cross-platform helper functions, such as line counts
## Functions using contextlib and cStringIO to suppress
## stdout/stderr for wormtable library functions (since
## we have moved away from system calls and can't catch
## the output of Popen communicate() any more!
import os
import sys
import contextlib

WIN_PLATFORM_NONFREE = False

RESULTLIMIT = 100

# stdout/stderr suppression idea taken from:
# http://stackoverflow.com/a/2829036
class DummyOutputFile(object):
    def write(self, x):
        pass
    
    def flush(self):
        pass

@contextlib.contextmanager
def no_console_output():
    save_stdout = sys.stdout
    save_stderr = sys.stderr
    sys.stdout = DummyOutputFile()
    sys.stderr = DummyOutputFile()
    yield
    sys.stdout = save_stdout
    sys.stderr = save_stderr

def get_os():
    if 'win' in platform.system().lower():
        WIN_PLATFORM_NONFREE = True

#line counter, from http://stackoverflow.com/a/27518377
#only difference is the use of f.read, and not f.raw.read
def _make_gen(reader):
    b = reader(1024 * 1024)
    while b:
        yield b
        b = reader(1024 * 1024)

def get_linecount(fname):
    f = open(fname, 'rb')
    f_gen = _make_gen(f.read)

    return sum(buf.count(b'\n') for buf in f_gen)
