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
Wormtable administration program.
"""
from __future__ import print_function
from __future__ import division

import re
import os
import sys
import argparse
import signal

import wormtable as wt
import wormtable.cli as cli

class ProgramRunner(object):
    """
    Class responsible for running the program, managing output streams
    etc.
    """
    def __init__(self, args):
        self._homedir = args.HOMEDIR
        self._db_cache_size = wt.DEFAULT_CACHE_SIZE
        self._table = wt.Table(self._homedir)

    def init(self):
        """
        Initialises the instance variables in this runner object.
        """
        if not self._table.exists():
            self.error("Table '{0}' not found".format(self._homedir))
        self._table.set_db_cache_size(self._db_cache_size)
        self._table.open("r")

    def format_size(self, n):
        """
        Returns a string formatting the specified value in bytes into a
        human readable format. Based on StackOverflow answer.
        """
        num = n
        for x in ['B  ','KiB','MiB','GiB']:
            if num < 1024.0:
                return "%3.1f %s" % (num, x)
            num /= 1024.0
        return "%3.1f %s" % (num, 'TiB')

    def cleanup(self):
        """
        Cleans up any open tables, indexes or files.
        """
        if self._table is not None:
            if self._table.is_open():
                self._table.close()

    def error(self, s):
        """
        Raises and error and exits.
        """
        print("Error:", s)
        sys.exit(1)


class ShowRunner(ProgramRunner):
    """
    Runner for the show command
    """
    def run(self):
        """
        Print out the details of the columns in the table.
        """
        t = self._table
        # get the max width for name
        max_name_width = 0
        for c in t.columns():
            n = len(c.get_name())
            if n > max_name_width:
                max_name_width = n
        fmt = "{0:>4}   {1:{name_width}} {2:<6} {3:>6}   {4:<6}   |   {5}"
        s = fmt.format("", "name", "type", "size", "n", "description",
                    name_width=max_name_width + 2)
        print("=" * (len(s) + 2))
        print(s)
        print("=" * (len(s) + 2))
        for c in t.columns():
            num_elements = c.get_num_elements()
            name = c.get_name()
            desc = c.get_description()
            s = fmt.format(c.get_position(), name, c.get_type_name(),
                    c.get_element_size(),
                    num_elements if num_elements > 0 else "var(1)", desc,
                    name_width=max_name_width + 2)
            print(s)

class ListRunner(ProgramRunner):
    """
    Program runner for the list command.
    """
    def run(self):
        """
        Prints out a summary of the details of this table and its indexes.
        """
        t = self._table
        n = len(t)
        mean_row_size = 0
        if n != 0:
            mean_row_size = int(t.get_total_row_size() / n)
        # print a summary of the table first
        fmt = "{0:<20}:{1:>15}"
        print(fmt.format("rows", n))
        print(fmt.format("data file size",
            self.format_size(t.get_data_file_size())))
        print(fmt.format("db file size",
            self.format_size(t.get_db_file_size())))
        print(fmt.format("minimum row size",
            self.format_size(t.get_min_row_size())))
        print(fmt.format("maximum row size",
            self.format_size(t.get_max_row_size())))
        print(fmt.format("mean row size",
            self.format_size(mean_row_size)))
        print(fmt.format("fixed region size",
            self.format_size(t.get_fixed_region_size())))
        names = sorted(t.indexes())
        if len(names) == 0:
            print("No indexes")
        else:
            max_name_width = 0
            print("Indexes:")
            max_name_width = max(len(n) for n in names) + 2
            fmt = "{0:{name_width}} {1:>10} {2:>3} | {3}"
            s = fmt.format("name", "size", "n", "colspec", name_width=max_name_width)
            print("=" * (len(s) + 2))
            print(s)
            print("=" * (len(s) + 2))
            for n in names:
                i = t.open_index(n)
                s = fmt.format(i.get_name(), self.format_size(i.get_db_file_size()),
                        len(i.key_columns()), i.get_colspec(), name_width=max_name_width)
                i.close()
                print(s)

class IndexProgramRunner(ProgramRunner):
    """
    Superclass of all program runners that have an index.
    """
    def __init__(self, args):
        super(IndexProgramRunner, self).__init__(args)
        self._index_name = args.NAME
        self._index = None

    def init(self):
        super(IndexProgramRunner, self).init()
        self._index = wt.Index(self._table, self._index_name)
        if not self._index.exists():
            self.error("Index '{0}' not found".format(self._index_name))
        self._index.open("r")

    def cleanup(self):
        if self._index is not None:
            if self._index.is_open():
                self._index.close()
        super(IndexProgramRunner, self).cleanup()

class HistRunner(IndexProgramRunner):
    """
    Runner for the index historgram command.
    """
    def run(self):
        counter = self._index.counter()
        cols = self._index.key_columns()
        n = len(cols)
        s = "\t".join([cols[j].get_name() for j in range(n)])
        s = "n\t" + s
        print("#", s)
        for k, v in counter.items():
            if n == 1:
                s = cols[0].format_value(k)
            else:
                s = "\t".join([cols[j].format_value(k[j]) for j in range(n)])
            print(v, "\t",  s)

class DeleteRunner(IndexProgramRunner):
    """
    Runner for the index delete command.
    """
    def run(self):
        self._index.close()
        self._index.delete()
        self._index = None

class AddRunner(ProgramRunner):
    """
    Runner for the index add command.
    """
    def __init__(self, args):
        super(AddRunner, self).__init__(args)
        self._colspec = args.COLSPEC
        self._index_name = args.name
        if args.name is None:
            self._index_name = self._colspec
        self._quiet = args.quiet
        self._force = args.force
        self._index_db_cache_size = args.cache_size
        self._index = None

    def init(self):
        super(AddRunner, self).init()
        self._index = wt.Index(self._table, self._index_name)
        if self._index.exists() and not self._force:
            s = "Index '{0}' exists; use --force to overwrite"
            self.error(s.format(self._index_name))
        self.parse_colspec()
        self._index.set_db_cache_size(self._index_db_cache_size)
        self._index.open("w")

    def parse_colspec(self):
        """
        Parses the specified column specification and adds the key columns
        and bin widths specified within.
        """
        for c in self._colspec.split("+"):
            col_name = c
            bin_width = 0
            m = re.search("\[.*\]$", c)
            if m is not None:
                g = m.group(0)
                col_name = c[:m.start(0)]
                bin_width = float(g.strip("[]"))
            col = self._table.get_column(col_name)
            self._index.add_key_column(col, bin_width)

    def run(self):
        """
        Create the index.
        """
        n = len(self._table)
        f = None
        monitor = cli.ProgressMonitor(n, "rows")
        def progress(processed_rows):
            monitor.update(processed_rows)
        def null(processed_rows):
            pass
        # TODO we must handle interrupts better here - clean
        # up partially built indexes. There is also a problem
        # with index files being left behind from builds that
        # were kill -9'd that Berkeley DB thinks are still held
        # open.
        f = null if self._quiet else progress
        self._index.build(f, max(1, int(n / 1000)))
        if not self._quiet:
            monitor.finish()

    def cleanup(self):
        if self._index is not None:
            if self._index.is_open():
                self._index.close()
        super(AddRunner, self).cleanup()

class DumpRunner(ProgramRunner):
    """
    Runner class for the dump command.
    """
    def __init__(self, args):
        super(DumpRunner, self).__init__(args)
        self._db_cache_size = args.cache_size
        self._index = None
        self._start = args.start
        self._stop = args.stop
        self._columns = None
        self._index_name = args.index
        self._column_ids = args.columns
        if args.index is not None:
            self._index = wt.Index(self._table, self._index_name)
            if not self._index.exists():
                self.error("Index '{0}' not found".format(self._index_name))

    def parse_index_key(self, key):
        """
        Parses the specified key from the command line into something
        that can be used as a key for this index.
        """
        l = []
        for c, k in zip(self._index.key_columns(), key.split(",")):
            v = str(k).encode()
            if c.get_type() == wt.WT_FLOAT:
                v = float(k)
            elif c.get_type() in [wt.WT_INT, wt.WT_UINT]:
                v = int(k)
            l.append(v)
        if len(self._index.key_columns()) == 1:
            ret = l[0]
        else:
            ret = tuple(l)
        return ret

    def init(self):
        super(DumpRunner, self).init()
        if self._index is not None:
            self._index.open("r")
            if self._start is not None:
                self._start = self.parse_index_key(self._start)
            else:
                self._start = wt.KEY_UNSET
            if self._stop is not None:
                self._stop = self.parse_index_key(self._stop)
            else:
                self._stop = wt.KEY_UNSET
        else:
            if self._start is not None:
                self._start = [int(self._start)]
            if self._stop is not None:
                self._stop = [int(self._stop)]

        self._columns = self._table.columns()
        if len(self._column_ids) > 0:
            self._columns = []
            for col_id in self._column_ids:
                try:
                    col_id = int(col_id)
                except ValueError:
                    pass
                c = self._table.get_column(col_id)
                self._columns.append(c)

    def run(self):
        if self._index is None:
            v = self._start
            start = 0 if v is None else v[0]
            v = self._stop
            stop = v if v is None else v[0]
            cursor = self._table.cursor(self._columns, start, stop)
        else:
            start = self._start
            stop = self._stop
            cursor = self._index.cursor(self._columns, start, stop)
        for row in cursor:
            s = ""
            for c, v in zip(self._columns, row):
                s = s + c.format_value(v) + "\t"
            print(s)


    def cleanup(self):
        if self._index is not None:
            if self._index.is_open():
                self._index.close()
        super(DumpRunner, self).cleanup()


def add_homedir_argument(parser):
    """
    Adds a positional homedir argument to the specified parser.
    """
    parser.add_argument("HOMEDIR",
        help="Wormtable home directory")

def add_colspec_argument(parser):
    """
    Adds a positional colspec argument to the specified parser.
    """
    parser.add_argument("COLSPEC",
        help="""Column specification for the index. A colspec
        is of the form n_1[w_1]+n_2[w_2]+...+n_k[w_k], where n_j is the
        name of the j_th column in the index and w_j is the optional
        width of the bins in the index. If w_j is not provided or
        equal to 0.0, index keys are not binned. For example,
        a colspec CHROM+POS defines an index on the columns CHROM
        and POS without binning; a colspec INFO.AF[0.1] defines
        an index on the column INFO.AF with a bin width of 0.1.
        """)


def wtadmin_main(cmdline_args=None):
    prog_description = "Wormtable administration program."
    parser = argparse.ArgumentParser(description=prog_description)
    cli.add_version_argument(parser)
    subparsers = parser.add_subparsers(title='subcommands',)

    # help
    show_parser = subparsers.add_parser("help",
            description = "wtadmin help",
            help="show this help message and exit")

    # show command
    show_parser = subparsers.add_parser("show",
            description = "Show the columns in the table",
            help="show details about the columns in the table")
    add_homedir_argument(show_parser)
    show_parser.set_defaults(runner=ShowRunner)

    # ls command
    ls_parser = subparsers.add_parser("ls",
            description="list details of the table and its indexes",
            help="list the indexes in the table")
    add_homedir_argument(ls_parser)
    ls_parser.set_defaults(runner=ListRunner)

    # index histogram command
    hist_parser = subparsers.add_parser("hist",
        help="""show the histogram for index NAME""",
        description="show the keys and counts from an index")
    add_homedir_argument(hist_parser)
    hist_parser.add_argument("NAME", help="name of the index")
    hist_parser.set_defaults(runner=HistRunner)

    # rm index command
    remove_parser = subparsers.add_parser("rm",
        help="delete an index",
        description="delete an index")
    add_homedir_argument(remove_parser)
    remove_parser.add_argument("NAME", help="name of the index")
    remove_parser.set_defaults(runner=DeleteRunner)

    # add index command
    add_parser = subparsers.add_parser("add",
            help="add a new index to the table",
            description="add a new index to the table")
    add_homedir_argument(add_parser)
    add_colspec_argument(add_parser)
    add_parser.add_argument("--quiet", "-q", action="store_true", default=False,
        help="suppress progress monitor and messages")
    add_parser.add_argument("--force", "-f", action="store_true", default=False,
        help="force over-writing of existing index")
    add_parser.add_argument("--name", "-n",
        help="name of the index (defaults to COLSPEC)")
    add_parser.add_argument("--cache-size", "-c", default="64M",
            help="""index cache size in bytes; suffixes K, M and G also supported.
                This option is very important for index build performance and
                should be set as large as possible; ideally, the entire index
                should fit into the cache. """)
    add_parser.set_defaults(runner=AddRunner)

    # dump command
    dump_parser = subparsers.add_parser("dump",
            help="dump the table to stdout",
            description="dump data from the table to stdout.")
    add_homedir_argument(dump_parser)
    dump_parser.add_argument("columns", metavar="COLUMN", nargs="*",
        help="Columns to dump - defaults to all columns")
    dump_parser.add_argument("--cache-size", "-c", default="64M",
            help="cache size in bytes; suffixes K, M and G also supported.")
    dump_parser.add_argument("--index", "-i", default=None,
            help="index to sort by when dumping rows")
    dump_parser.add_argument("--start", "-s", default=None,
            help="""start value to print. This is a comma delimited series
                of values for each column in the index. Eg. --start=AA,A""")
    dump_parser.add_argument("--stop", "-t", default=None,
            help="""stop value to print. This is a comma delimited series
                of values for each column in the index.""")
    dump_parser.set_defaults(runner=DumpRunner)

    if os.name == "posix":
        # Set signal handler for SIGPIPE to quietly kill the program.
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    args = parser.parse_args(cmdline_args)
    if "runner" not in args:
        parser.print_help()
    else:
        runner = args.runner(args)
        try:
            runner.init()
            runner.run()
        finally:
            runner.cleanup()
