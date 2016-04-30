#
# Copyright (C) 2013, wormtable developers (see AUTHORS.txt).
#
# This file is part of wormtable.
#
# Wormtable is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Wormtable is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with wormtable.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Command line interface utilities for wormtable.
"""
from __future__ import print_function
from __future__ import division

import gzip
import os
import sys
import time

import wormtable as wt


def add_version_argument(parser):
    """
    Adds a version argument to the specified argparse parser.
    """
    parser.add_argument(
        "-V", "--version", action='version',
        version='%(prog)s {}'.format(wt.__version__))


class ProgressMonitor(object):
    """
    Class representing a progress monitor for a terminal based interface.
    """
    def __init__(self, total, units):
        self.__total = total
        self.__units = units
        self.__progress_width = 40
        self.__bar_index = 0
        self.__bars = "/-\\|"
        self.__start_time = time.clock()

    def update(self, processed):
        """
        Updates this progress monitor to display the specified number
        of processed items.
        """
        complete = processed / self.__total
        filled = int(complete * self.__progress_width)
        spaces = self.__progress_width - filled
        bar = self.__bars[self.__bar_index]
        self.__bar_index = (self.__bar_index + 1) % len(self.__bars)
        elapsed = max(1, time.clock() - self.__start_time)
        rate = processed / elapsed
        s = '\r[{0}{1}] {2:5.1f}% @{3:8.1E} {4}/s {5}'.format('#' * filled,
            ' ' * spaces, complete * 100, rate, self.__units, bar)
        sys.stdout.write(s)
        sys.stdout.flush()

    def finish(self):
        """
        Completes the progress monitor.
        """
        print()

BROKEN_GZIP_MESSAGE = """
An error occurred reading the input gzip file. This is probably due to a
bug in recent versions of Python, resulting in an error when trying
to read BGZF files. See http://bugs.python.org/issue17666
To convert this file to wormtable, you must decompress it first using gunzip.
"""


class FileReader(object):
    """
    A class for reading data files from a variety of sources and
    with progress updating.
    """
    def __init__(self, in_file):
        if in_file == '-':
            self.__input_file = sys.stdin
            if sys.version_info[:2] >= (3, 1):
                try:
                    self.__input_file = sys.stdin.buffer
                except AttributeError:
                    # When we're testing, we replace stdin with an ordinary
                    # file. This does not support buffer, but is also not
                    # needed so we can skip this step
                    pass
            self.__progress_monitor = None
            self.__input_file_size = None
            self.__progress_file = None
        else:
            if in_file.endswith(".gz"):
                # Detect broken GZIP handling in 2.7/3.2 and others and abort
                # TODO this has been fixed upstream and can be removed at
                # some point.
                f = gzip.open(in_file, "rb")
                try:
                    s = f.readline()
                except Exception as e:
                    print(BROKEN_GZIP_MESSAGE)
                    sys.exit(1)
                f.close()
                # Carry on as before
                self.__input_file = gzip.open(in_file, "rb")
                self.__progress_file = self.__input_file.fileobj
            else:
                self.__input_file = open(in_file, "rb")
                self.__progress_file = self.__input_file
            statinfo = os.stat(in_file)
            self.__input_file_size = statinfo.st_size
        self.__progress_update_rows = 2**32
        self.__progress_monitor = None

    def get_progress_update_rows(self):
        """
        Returns the number of rows after which we should update the progress
        monitor.
        """
        return self.__progress_update_rows

    def set_progress_update_rows(self, update_rows):
        """
        Sets the number of rows after which we should update progress
        to the specified value.
        """
        self.__progress_update_rows = update_rows

    def get_input_file(self):
        """
        Returns the File object that is the source of the information
        in this reader.
        """
        return self.__input_file

    def set_progress(self, progress):
        """
        If progress is True turn on progress monitoring for this GTF reader.
        """
        if progress:
            self.__progress_monitor = ProgressMonitor(self.__input_file_size,
                    "bytes")
            self.__progress_monitor.update(0)
            self.__progress_update_rows = 100
            if self.__input_file_size > 2**30:
                self.__progress_update_rows = 1000

    def update_progress(self):
        """
        Reads the position we are at in the underlying file and uses this to
        update the progress bar, if used.
        """
        if self.__progress_monitor is not None:
            t = self.__progress_file.tell()
            self.__progress_monitor.update(t)

    def finish_progress(self):
        """
        Finishes up the progress monitor, if in use.
        """
        if self.__progress_monitor is not None:
            self.update_progress()
            self.__progress_monitor.finish()

    def close(self):
        """
        Closes any open files on this Reader.
        """
        self.__input_file.close()
        if self.__progress_file is not None:
            self.__progress_file.close()
