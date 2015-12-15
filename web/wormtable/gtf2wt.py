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
GTF conversion tool for wormtable. This is a strict parser for GTF2.2 as
defined by http://mblab.wustl.edu/GTF22.html. In particular, all annotation
fields other than the  gene_id and transcript_id are ignored.
"""
from __future__ import print_function
from __future__ import division

import os
import sys
import gzip
import shutil
import argparse
import tempfile
import multiprocessing

import wormtable as wt
import wormtable.cli as cli

# GTF fixed columns
SEQNAME = b"seqname"
SOURCE = b"source"
FEATURE = b"feature"
START = b"start"
END = b"end"
SCORE = b"score"
STRAND = b"strand"
FRAME = b"frame"

# Attributes
GENE_ID = b"gene_id"
TRANSCRIPT_ID = b"transcript_id"

# Descriptions; these descriptions are taken from the definition of GTF
# http://mblab.wustl.edu/GTF22.html
SEQNAME_DESC = b"The name of the sequence"
SOURCE_DESC = b"The source of this feature"
FEATURE_DESC = b"The feature type name"
START_DESC = b"Start of the feature; must be less than or equal to end"
END_DESC = b"End of the feature"
SCORE_DESC = b"""Indicates a degree of confidence in the feature's existence
    and coordinates."""
STRAND_DESC = b"One of '+', '-' or '.'"
FRAME_DESC = b"""0 indicates that the feature begins with a whole codon at
    the 5' most base. 1 means that there is one extra base (the third
    base of a codon) before the first whole codon and 2 means that
    there are two extra bases (the second and third bases of the codon)
    before the first codon. Note that for reverse strand features, the 5'
    most base is the <end> coordinate"""
GENE_ID_DESC = b"""A globally unique identifier for the genomic locus of the
    transcript. If empty, no gene is associated with this feature."""
TRANSCRIPT_ID_DESC = b"""A globally unique identifier for the predicted
    transcript.  If empty, no transcript is associated with this feature."""

GTF_FIXED_COLUMNS = [SEQNAME, SOURCE, FEATURE, START, END, SCORE, STRAND, FRAME]
GTF_ATTRIBUTE_COLUMNS = [GENE_ID, TRANSCRIPT_ID]

# Special values in GTF
MISSING_VALUE = b"."

class GTFReader(cli.FileReader):
    """
    Parse GTF files.
    """
    def rows(self):
        """
        Returns an iterator over the rows in this GTF file.
        """
        num_rows = 0
        input_file = self.get_input_file()
        update_rows = self.get_progress_update_rows()
        all_columns = GTF_FIXED_COLUMNS + GTF_ATTRIBUTE_COLUMNS
        empty_row = [None for c in all_columns]
        num_fixed_cols = len(GTF_FIXED_COLUMNS)
        gene_id_index = all_columns.index(GENE_ID)
        transcript_id_index = all_columns.index(TRANSCRIPT_ID)
        for line in input_file:
            row = list(empty_row)
            tokens = line.split(b"\t")
            for j in range(num_fixed_cols):
                if tokens[j] != MISSING_VALUE:
                    row[j] = tokens[j]
            # parse out the attributes
            attrs = tokens[num_fixed_cols].split(b";")
            # GENE_ID and TRANSCRIPT_ID must be the first two attributes,
            # not necessarily in that order.
            for s in attrs[:2]:
                k, v = s.split()
                index = 0
                if k == GENE_ID:
                    index = gene_id_index
                else:
                    index = transcript_id_index
                row[index] = v.strip(b"\"")
            yield row
            num_rows += 1
            if num_rows % update_rows == 0:
                self.update_progress()
        self.finish_progress()

class ProgramRunner(object):
    """
    Class responsible for running the gtf2wt program.
    """
    def __init__(self, args):
        self.__destination = args.DEST
        self.__db_cache_size = args.cache_size
        self.__force = args.force
        self.__progress = not args.quiet
        self.__quiet = args.quiet
        self.__tmp_dirs = []
        self.__tmp_files = []
        self.__table = None
        self.__column_map = None
        self.__reader = GTFReader(args.SOURCE)
        self.__writer = None
        # if reading from STDIN, set progress monitor to False regardless
        if args.SOURCE == '-':
            self.__progress = False

    def __define_schema(self):
        """
        Defines the schema for a GTF file.
        """
        t = self.__table
        t.add_id_column(4)
        t.add_char_column(SEQNAME, SEQNAME_DESC)
        t.add_char_column(SOURCE, SOURCE_DESC)
        t.add_char_column(FEATURE, FEATURE_DESC)
        t.add_uint_column(START, START_DESC, 5)
        t.add_uint_column(END, END_DESC, 5)
        t.add_float_column(SCORE, SCORE_DESC, 4)
        t.add_char_column(STRAND, STRAND_DESC, 1)
        t.add_uint_column(FRAME, FRAME_DESC, 1)
        t.add_char_column(GENE_ID, GENE_ID_DESC)
        t.add_char_column(TRANSCRIPT_ID, TRANSCRIPT_ID_DESC)


    def write_table(self):
        """
        Writes the table, assuming that we have created a directory with
        a table ready for writing.
        """
        os.mkdir(self.__destination)
        self.__table = wt.Table(self.__destination)
        self.__define_schema()
        self.__table.set_db_cache_size(self.__db_cache_size)
        self.__table.open("w")
        self.__reader.set_progress(self.__progress)
        for r in self.__reader.rows():
            self.__table.append_encoded([None] + r)
        self.__table.close()

    def run(self):
        """
        Top level entry point.
        """
        if os.path.exists(self.__destination):
            if self.__force:
                if os.path.isdir(self.__destination):
                    shutil.rmtree(self.__destination)
                else:
                    os.unlink(self.__destination)
            else:
                s = "'{0}' exists; use -f to overwrite".format(self.__destination)
                self.error(s)
        self.write_table()

    def error(self, s):
        """
        Raises and error and exits.
        """
        print("Error:", s)
        sys.exit(0)


def gtf2wt_main(args=None):
    prog_description = "Convert a GTF file to Wormtable format."
    parser = argparse.ArgumentParser(description=prog_description)
    cli.add_version_argument(parser)
    parser.add_argument("SOURCE",
        help="GTF file to convert (use '-' for STDIN)")
    parser.add_argument("DEST",
        help="Output wormtable home directory")
    parser.add_argument("--quiet", "-q", action="store_true",
        default=False,
        help="Suppress progress monitor")
    parser.add_argument("--force", "-f", action="store_true", default=False,
        help="Force over-writing of existing wormtable")
    parser.add_argument("--cache-size", "-c", default="64M",
        help="cache size in bytes; suffixes K, M and G also supported.")
    parsed_args = parser.parse_args(args)
    runner = ProgramRunner(parsed_args)
    runner.run()
