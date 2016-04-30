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
Wormtable is a read-once write-many table for large scale datasets.

This is the high-level module for wormtable, and provides a convenient
interface to the low-level interface defined in _wormtable. The low
level interface is not intended to be used directly and is subject
to change in non-backward compatible ways.
"""
from __future__ import print_function
from __future__ import division

import os
import glob
import shutil
import collections
from xml.dom import minidom
from xml.etree import ElementTree

import _wormtable

TABLE_METADATA_VERSION = "0.3"
INDEX_METADATA_VERSION = "0.4"

DEFAULT_CACHE_SIZE = 16 * 2**20  # 16M
DEFAULT_CACHE_SIZE_STR = "16M"

WT_INT = _wormtable.WT_INT
WT_UINT = _wormtable.WT_UINT
WT_FLOAT = _wormtable.WT_FLOAT
WT_CHAR = _wormtable.WT_CHAR

WT_READ = _wormtable.WT_READ
WT_WRITE = _wormtable.WT_WRITE
WT_VAR_1 = _wormtable.WT_VAR_1
WT_VAR_2 = _wormtable.WT_VAR_2

KEY_UNSET = "KEY_UNSET"


def open_table(homedir, db_cache_size=DEFAULT_CACHE_SIZE_STR):
    """
    Returns a table opened in read mode with cache size
    set to the specified value. This is the recommended
    interface when opening tables for reading.

    See :ref:`performance-cache` for details on setting cache sizes.
    The cache size may be either an integer specifying the size in
    bytes or a string with the optional suffixes K, M or G.

    :param homedir: the filesystem path for the wormtable home directory
    :type homedir: str
    :param db_cache_size: The Berkeley DB cache size for the table.
    :type db_cache_size: str or int.
    """
    t = Table(homedir)
    if not t.exists():
        msg = "Wormtable home directory '{0}' not found or not in "\
              "wormtable format.".format(homedir)
        raise IOError(msg)
    t.set_db_cache_size(db_cache_size)
    t.open("r")
    return t


class Column(object):
    """
    Class representing a column in a table.
    """
    ELEMENT_TYPE_STRING_MAP = {
        WT_INT: "int",
        WT_UINT: "uint",
        WT_CHAR: "char",
        WT_FLOAT: "float",
    }

    def __init__(self, ll_object):
        self.__ll_object = ll_object

    def __str__(self):
        s = "NULL Column"
        if self.__ll_object is not None:
            s = "'{0}':{1}({2})".format(self.get_name(), self.get_type_name(),
                    self.get_num_elements())
        return s

    def get_ll_object(self):
        """
        Returns the low level Column object that this class is a facade for.
        """
        return self.__ll_object

    def get_position(self):
        """
        Returns the position of this column in the table.
        """
        return self.__ll_object.position

    def get_name(self):
        """
        Returns the name of this column. This is the unique identifier for
        a column.
        """
        return self.__ll_object.name.decode()

    def get_description(self):
        """
        Returns the description of this column. This is an optional string
        describing the purpose of a column.
        """
        return self.__ll_object.description.decode()

    def get_type(self):
        """
        Returns the type code for this column. This is
        one of WT_INT,  WT_UINT, WT_FLOAT or  WT_CHAR.
        """
        return self.__ll_object.element_type

    def get_type_name(self):
        """
        Returns the string representation of the type of this Column.
        """
        return self.ELEMENT_TYPE_STRING_MAP[self.__ll_object.element_type]

    def get_element_size(self):
        """
        Returns the size of each element in the column in bytes.
        """
        return self.__ll_object.element_size

    def get_num_elements(self):
        """
        Returns the number of elements in this column. This is either a
        positive integer >= 1 or WT_VAR1. If the number of elements
        is WT_VAR1, the number of elements in the column is variable,
        from 0 to 255.
        """
        return self.__ll_object.num_elements

    def format_value(self, v):
        """
        Formats the specified value from this column for printing.
        """
        if v is None:
            s = "NA"
        else:
            n = self.get_num_elements()
            if self.get_type() == WT_CHAR:
                s = v.decode()
            elif n == 1:
                s = str(v)
            else:
                s = ",".join(str(u) for u in v)
                s = "(" + s + ")"
        return s

    def get_xml(self):
        """
        Returns an ElementTree.Element representing this Column.
        """
        n = self.get_num_elements()
        if n == WT_VAR_1:
            num_elements = "var(1)"
        elif n == WT_VAR_2:
            num_elements = "var(2)"
        else:
            num_elements = str(self.get_num_elements())
        d = {
            "name":self.get_name(),
            "description":self.get_description(),
            "element_size":str(self.get_element_size()),
            "num_elements":num_elements,
            "element_type":self.get_type_name()
        }
        return ElementTree.Element("column", d)

    @classmethod
    def parse_xml(theclass, xmlcol):
        """
        Parses the specified XML column description and returns a new
        Column instance.
        """
        reverse = {}
        for k, v in theclass.ELEMENT_TYPE_STRING_MAP.items():
            reverse[v] = k
        if xmlcol.tag != "column":
            raise ValueError("invalid xml")
        name = xmlcol.get("name").encode()
        description = xmlcol.get("description").encode()
        # TODO some error checking here.
        element_size = int(xmlcol.get("element_size"))
        s = xmlcol.get("num_elements")
        if s == "var(1)":
            num_elements = WT_VAR_1
        elif s == "var(2)":
            num_elements = WT_VAR_2
        else:
            num_elements = int(s)
        element_type = reverse[xmlcol.get("element_type")]
        col = _wormtable.Column(name, description, element_type, element_size,
                num_elements)
        return theclass(col)


class Database(object):
    """
    The superclass of database objects. Databases are located in a home
    directory and are backed by a two files: a database file and an
    xml metadata file.
    """
    DB_SUFFIX = ".db"

    def __init__(self, homedir, db_name):
        """
        Allocates a new database object held in the specified homedir
        with the specified db_name.
        """
        self.__homedir = homedir
        self.__db_name = db_name
        self.__db_cache_size = DEFAULT_CACHE_SIZE
        self.__ll_object = None
        self.__open_mode = None

    def __del__(self):
        if self.is_open():
            # TODO add in a logging.warning message here.
            # print("closing dangling table.", self.__ll_object)
            try:
                self.__ll_object.close()
            finally:
                self.__ll_object = None

    def __enter__(self):
        """
        Context manager entry.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit; closes the database.
        """
        self.close()
        return False

    def get_ll_object(self):
        """
        Returns the low-level object that this Database is a facade for.
        """
        return self.__ll_object

    def _create_ll_object(self, build):
        """
        Returns a newly created instance of the low-level object that this
        Database is a facade for.
        """
        raise NotImplementedError()

    def exists(self):
        """
        Returns True if this Database exists.
        """
        p1 = os.path.exists(self.get_metadata_path())
        p2 = os.path.exists(self.get_db_path())
        return p1 and p2

    def get_homedir(self):
        """
        Returns the home directory for this database object.
        """
        return self.__homedir

    def get_db_name(self):
        """
        Returns the db name of this database object.
        """
        return self.__db_name

    def get_db_cache_size(self):
        """
        Returns the cache size for this database in bytes.
        """
        return self.__db_cache_size

    def get_db_path(self):
        """
        Returns the path of the permanent file used to store the database.
        """
        return os.path.join(self.get_homedir(), self.get_db_name() +
                self.DB_SUFFIX)

    def get_db_build_path(self):
        """
        Returns the path of the file used to build the database.
        """
        s = "_build_{0}_{1}{2}".format(os.getpid(), self.get_db_name(),
                self.DB_SUFFIX)
        return os.path.join(self.get_homedir(), s)

    def get_db_file_size(self):
        """
        Returns the size of the database file in bytes.
        """
        statinfo = os.stat(self.get_db_path())
        return statinfo.st_size

    def get_metadata_path(self):
        """
        Returns the path of the file used to store metadata for the
        database.
        """
        return os.path.join(self.get_homedir(), self.get_db_name() + ".xml")

    def set_db_cache_size(self, db_cache_size):
        """
        Sets the cache size to the specified value.
        If db_cache_size is a string, it can be suffixed with
        K, M or G to specify units of Kibibytes, Mibibytes or Gibibytes.

        This must be called before a table is opened, and has no effect
        on a table that is already open.

        See :ref:`performance-cache` for details on setting cache sizes.

        :param db_cache_size: the size of the cache
        :type db_cache_size: str or int
        """
        if isinstance(db_cache_size, str):
            s = db_cache_size
            d = {"K":2**10, "M":2**20, "G":2**30}
            multiplier = 1
            value = s
            if s.endswith(tuple(d.keys())):
                value = s[:-1]
                multiplier = d[s[-1]]
            n = int(value)
            self.__db_cache_size = n * multiplier
        else:
            self.__db_cache_size = int(db_cache_size)

    def write_metadata(self, filename):
        """
        Writes the metadata for this database to the specified file.
        """
        tree = self.get_metadata()
        root = tree.getroot()
        s = "Do not edit this file!"
        comment = ElementTree.Comment(s)
        root.insert(0, comment)
        raw_xml = ElementTree.tostring(root, 'utf-8')
        reparsed = minidom.parseString(raw_xml)
        pretty = reparsed.toprettyxml(indent="  ")
        with open(filename, "w") as f:
            f.write(pretty)

    def read_metadata(self):
        """
        Reads metadata for this database from the metadata file
        and calls set_metadata with the result.
        """
        tree = ElementTree.parse(self.get_metadata_path())
        self.set_metadata(tree)

    def finalise_build(self):
        """
        Move the build file to its final location and write the metadata file.
        """
        new = self.get_db_path()
        old = self.get_db_build_path()
        shutil.move(old, new)
        self.write_metadata(self.get_metadata_path())

    def is_open(self):
        """
        Returns True if this database is open for reading or writing.
        """
        return self.__ll_object is not None

    def get_open_mode(self):
        """
        Returns the mode that this database is opened in, WT_READ or
        WT_WRITE. If the database is not open, return None.
        """
        return self.__open_mode

    def open(self, mode):
        """
        Opens this table in the specified mode. Mode must be one of
        'r' or 'w'.

        :param: mode: The mode to open the table in.
        :type: mode: str
        """
        modes = {'r': _wormtable.WT_READ, 'w': _wormtable.WT_WRITE}
        if mode not in modes:
            raise ValueError("mode string must be one of 'r' or 'w'")
        m = modes[mode]
        self.__open_mode = None
        self.__ll_object = None
        build = False
        if m == WT_WRITE:
            build = True
        else:
            self.read_metadata()
        llo = self._create_ll_object(build)
        llo.open(m)
        self.__ll_object = llo
        self.__open_mode = m

    def close(self):
        """
        Closes this database object, freeing underlying resources.
        """
        try:
            self.__ll_object.close()
            if self.__open_mode == WT_WRITE:
                self.finalise_build()
        finally:
            self.__open_mode = None
            self.__ll_object = None

    def delete(self):
        """
        Deletes the DB and metadata files for this database.
        """
        self.verify_closed()
        os.unlink(self.get_db_path())
        os.unlink(self.get_metadata_path())

    def verify_closed(self):
        """
        Ensures this database is closed.
        """
        if self.is_open():
            raise ValueError("Database must be closed")

    def verify_open(self, mode=None):
        """
        Ensures this database is open in the specified mode..
        """
        if mode is None:
            if not self.is_open():
                raise ValueError("Database must be opened")
        else:
            if self.__open_mode != mode or not self.is_open():
                m = {WT_WRITE: "write", WT_READ: "read"}
                s = "Database must be opened in {0} mode".format(m[mode])
                raise ValueError(s)


class Table(Database):
    """
    The main storage table class.
    """
    DB_NAME = "table"
    DATA_SUFFIX = ".dat"
    PRIMARY_KEY_NAME = "row_id"

    def __init__(self, homedir):
        Database.__init__(self, homedir, self.DB_NAME)
        self.__columns = []
        self.__column_name_map = {}
        self.__num_rows = 0
        self.__total_row_size = 0
        self.__min_row_size = 0
        self.__max_row_size = 0

    def get_data_path(self):
        """
        Returns the path of the permanent data file.
        """
        return os.path.join(self.get_homedir(), self.get_db_name() +
                self.DATA_SUFFIX)

    def get_data_build_path(self):
        """
        Returns the path of the file used to build the database.
        """
        s = "_build_{0}_{1}{2}".format(os.getpid(), self.get_db_name(),
                self.DATA_SUFFIX)
        return os.path.join(self.get_homedir(), s)

    def get_data_file_size(self):
        """
        Returns the size of the data file in bytes.
        """
        statinfo = os.stat(self.get_data_path())
        return statinfo.st_size

    def finalise_build(self):
        """
        Finalise the build by moving the data and db files to their
        permanent values.
        """
        super(Table, self).finalise_build()
        new = self.get_data_path()
        old = self.get_data_build_path()
        shutil.move(old, new)

    def delete(self):
        """
        Deletes this table.
        """
        super(Table, self).delete()
        os.unlink(self.get_data_path())

    def get_total_row_size(self):
        """
        Returns the total number of bytes stored within rows in this table.
        """
        return self.__total_row_size

    def get_min_row_size(self):
        """
        Returns the size of the smallest row in this table in bytes.
        """
        return self.__min_row_size

    def get_max_row_size(self):
        """
        Returns the size of the largest row in this table in bytes.
        """
        return self.__max_row_size

    def _create_ll_object(self, build):
        """
        Returns a new instance of _wormtable.Table using either the build
        or permanent locations for the db and data files.
        """
        if build:
            db_file = self.get_db_build_path().encode()
            data_file = self.get_data_build_path().encode()
        else:
            db_file = self.get_db_path().encode()
            data_file = self.get_data_path().encode()
        ll_cols = [c.get_ll_object() for c in self.__columns]
        t = _wormtable.Table(db_file, data_file, ll_cols,
                self.get_db_cache_size())
        return t

    def get_fixed_region_size(self):
        """
        Returns the size of the fixed region in rows. This is the minimum
        size that a row can be; if there are no variable sized columns in
        the table, then this is the exact size of each row.
        """
        return self.get_ll_object().fixed_region_size

    # Helper methods for adding Columns of the various types.

    def add_id_column(self, size=4):
        """
        Adds the ID column with the specified size in bytes.
        """
        name = self.PRIMARY_KEY_NAME
        desc = 'Primary key column'
        self.add_uint_column(name, desc, size, 1)

    def add_uint_column(self, name, description="", size=2, num_elements=1):
        """
        Creates a new unsigned integer column with the specified name,
        element size (in bytes) and number of elements. If num_elements=0
        then the column can hold a variable number of elements.
        """
        self.add_column(name, description, WT_UINT, size, num_elements)

    def add_int_column(self, name, description="", size=2, num_elements=1):
        """
        Creates a new integer column with the specified name,
        element size (in bytes) and number of elements. If num_elements=0
        then the column can hold a variable number of elements.
        """
        self.add_column(name, description, WT_INT, size, num_elements)

    def add_float_column(self, name, description="", size=4, num_elements=1):
        """
        Creates a new float column with the specified name,
        element size (in bytes) and number of elements. If num_elements=0
        then the column can hold a variable number of elements. Only 4 and
        8 byte floats are supported by wormtable; these correspond to the
        usual float and double types.
        """
        self.add_column(name, description, WT_FLOAT, size, num_elements)

    def add_char_column(self, name, description="", num_elements=0):
        """
        Creates a new character column with the specified name, description
        and number of elements. If num_elements=0 then the column can hold
        variable length strings; otherwise, it can contain strings of a fixed
        length only.
        """
        self.add_column(name, description, WT_CHAR, 1, num_elements)

    def add_column(self, name, description, element_type, size, num_elements):
        """
        Creates a new column with the specified name, description, element type,
        element size and number of elements.
        """
        if self.is_open():
            raise ValueError("Cannot add columns to open table")
        nb = name
        if isinstance(name, str):
            nb = name.encode()
        db = description
        if isinstance(description, str):
            db = description.encode()
        col = _wormtable.Column(nb, db, element_type, size, num_elements)
        self.__columns.append(Column(col))

    # Methods for accessing the columns
    def columns(self):
        """
        Returns the list of columns in this table.
        """
        return list(self.__columns)

    def get_column(self, col_id):
        """
        Returns the :class:`Column` corresponding to the specified id. If this is an
        integer, we return the column at this position; if it is a string
        we return the column with the specified name.

        :param: col_id: the column idenifier
        :type: col_id: str or int
        """
        ret = None
        if isinstance(col_id, int):
            ret = self.__columns[col_id]
        else:
            k = self.__column_name_map[col_id]
            ret = self.__columns[k]
        return ret

    def translate_columns(self, columns):
        """
        Translates the specified list of column identifiers into a list
        of Column instances. Column identifiers may be strings, integers
        or Column instances.
        """
        cols = []
        for col_id in columns:
            if isinstance(col_id, Column):
                cols.append(col_id)
            elif isinstance(col_id, int):
                cols.append(self.__columns[col_id])
            else:
                cols.append(self.get_column(col_id))
        return cols

    def read_schema(self, filename):
        """
        Reads the schema from the specified file and sets up the columns
        in this table accordingly.
        """
        tree = ElementTree.parse(filename)
        root = tree.getroot()
        if root.tag != "schema":
            raise ValueError("root element must be <schema>")
        version = root.get("version")
        if version is None:
            raise ValueError("invalid xml: schema version missing")
        supported_versions = [TABLE_METADATA_VERSION]
        if version not in supported_versions:
            raise ValueError("Unsupported schema version.")
        address_size = root.get("address_size")
        if address_size is None:
            raise ValueError("invalid xml: schema address_size missing")
        if address_size != "2":
            raise ValueError("Unsupported address size.")
        self._parse_schema_xml(root)

    def write_schema(self, filename):
        """
        Writes the schema for this table to the specified file in XML format.
        """
        root = self._generate_schema_xml()
        s = "Edit this candidate schema to suit your needs."
        comment = ElementTree.Comment(s)
        root.insert(0, comment)
        root.set("version", TABLE_METADATA_VERSION)
        raw_xml = ElementTree.tostring(root, 'utf-8')
        reparsed = minidom.parseString(raw_xml)
        pretty = reparsed.toprettyxml(indent="  ")
        with open(filename, "w") as f:
            f.write(pretty)

    def _generate_schema_xml(self):
        """
        Generates the XML representing the schema for this table.
        """
        schema = ElementTree.Element("schema")
        schema.set("address_size", "2")
        columns = ElementTree.Element("columns")
        schema.append(columns)
        for c in self.__columns:
            columns.append(c.get_xml())
        return schema

    def _generate_stats_xml(self):
        """
        Generates the XML representing the statistics for this table.
        """
        stats = ElementTree.Element("stats")
        l = [
            ("num_rows", self.__num_rows),
            ("max_row_size", self.__max_row_size),
            ("min_row_size", self.__min_row_size),
            ("total_row_size", self.__total_row_size)
        ]
        for name, value in l:
            d = {"name":name, "value":str(value)}
            s = ElementTree.Element("stat", d)
            stats.append(s)
        return stats

    def get_metadata(self):
        """
        Returns an ElementTree instance describing the metadata for this
        Table.
        """
        d = {"version":TABLE_METADATA_VERSION}
        root = ElementTree.Element("table", d)
        root.append(self._generate_schema_xml())
        root.append(self._generate_stats_xml())
        return ElementTree.ElementTree(root)

    def _parse_schema_xml(self, schema):
        """
        Parses the schema xml and updates the state of this table.
        """
        xml_columns = schema.find("columns")
        for xmlcol in xml_columns.getchildren():
            col = Column.parse_xml(xmlcol)
            self.__column_name_map[col.get_name()]= len(self.__columns)
            self.__columns.append(col)

    def _parse_stats_xml(self, stats):
        """
        Parses the specified XML to retrieve the statistics for this table.
        """
        for stat in stats.getchildren():
            name = stat.get("name")
            value = stat.get("value")
            # TODO this really isn't very good at all.
            if name == "num_rows":
                self.__num_rows = int(value)
            elif name == "max_row_size":
                self.__max_row_size = int(value)
            elif name == "min_row_size":
                self.__min_row_size = int(value)
            elif name == "total_row_size":
                self.__total_row_size = int(value)
            else:
                raise ValueError("unknown table statistic '" + name + "'")

    def set_metadata(self, tree):
        """
        Sets up this Table to reflect the metadata in the specified xml
        ElementTree.
        """
        root = tree.getroot()
        # Be nice to people using beta version or older; this can be
        # removed pretty soon. TODO
        if root.tag == "schema":
            raise ValueError("""
                You are trying to read a table built with a pre-release version
                of wormtable which is not compatible. You must rebuild this table.
                Sorry.""")
        if root.tag != "table":
            raise ValueError("invalid xml")
        version = root.get("version")
        if version is None:
            raise ValueError("invalid xml")
        supported_versions = [TABLE_METADATA_VERSION]
        if version not in supported_versions:
            raise ValueError("Unsupported schema version - rebuild required.")
        schema = root.find("schema")
        self._parse_schema_xml(schema)
        stats = root.find("stats")
        self._parse_stats_xml(stats)


    def append(self, row):
        """
        Appends the specified row to this table.
        """
        t = self.get_ll_object()
        j = 0
        for v in row:
            if v is not None:
                t.insert_elements(j, v)
            j += 1
        t.commit_row()
        self.__num_rows += 1

    def append_encoded(self, row):
        """
        Appends the specified row to this table.
        """
        t = self.get_ll_object()
        j = 0
        for v in row:
            if v is not None:
                t.insert_encoded_elements(j, v)
            j += 1
        t.commit_row()
        self.__num_rows += 1


    def __len__(self):
        """
        Implement the len(t) function.
        """
        self.verify_open()
        mode = self.get_open_mode()
        if mode == WT_READ:
            if self.__num_rows == 0:
                self.__num_rows = self.get_ll_object().get_num_rows()
        return self.__num_rows

    def __getitem__(self, key):
        """
        Implements the t[key] function.
        """
        self.verify_open(WT_READ)
        t = self.get_ll_object()
        ret = None
        n = len(self)
        if isinstance(key, slice):
            ret = [self[j] for j in range(*key.indices(n))]
        elif isinstance(key, int):
            k = key
            if k < 0:
                k = n + k
            if k >= n:
                raise IndexError("table position out of range")
            ret = t.get_row(k)
        else:
            raise TypeError("table positions must be integers")
        return ret

    def __update_stats(self):
        """
        Updates the statistics about the underlying database.
        """
        t = self.get_ll_object()
        self.__total_row_size = t.total_row_size
        self.__num_rows = t.num_rows
        self.__min_row_size = t.min_row_size
        self.__max_row_size = t.max_row_size

    def close(self):
        """
        Closes this table freeing all underlying resources.
        """
        self.verify_open()
        mode = self.get_open_mode()
        if mode == WT_WRITE:
            self.__update_stats()
        try:
            Database.close(self)
        finally:
            self.__num_rows = 0
            self.__columns = []
            self.__column_name_map = {}


    def cursor(self, columns, start=0, stop=None):
        """
        Returns a cursor over the rows in this table, retrieving only
        the specified columns. Rows are returned as Tuple objects, with the
        value for each column in the same position as the corresponding
        column in the list of columns provided.

        The columns specified may be either :class:`Column` instances, integers
        or strings. If an integer is provided, the column
        at the specified position is used and if a string is provided, the column
        with the specified identifier is used. These may be mixed arbitrarily.

        The *start* and *stop* arguments are directly analogous to the built in
        :func:`range` function. The cursor will iterate over all rows such that
        the *start* <= row_id < stop. Note that *start* is inclusive, and
        *stop* is exclusive.

        :param columns: columns to retrieve from the table
        :type columns: sequence of column identifiers
        :param start: the row id of the first row returned
        :type start: int
        :param stop: the row id of the last row returned, minus 1.
        :type stop: int
        """
        self.verify_open(WT_READ)
        col_pos = [c.get_position() for c in self.translate_columns(columns)]
        tri = _wormtable.TableRowIterator(self.get_ll_object(), col_pos)
        tri.set_min(start)
        if stop is not None:
            tri.set_max(stop)
        return tri

    def indexes(self):
        """
        Returns an interator over the names of the indexes in this table.
        """
        self.verify_open(WT_READ)
        prefix = os.path.join(self.get_homedir(), Index.DB_PREFIX)
        suffix = Index.DB_SUFFIX
        for g in glob.glob(prefix + "*" + suffix):
            name = g.replace(prefix, "")
            name = name.replace(suffix, "")
            yield name


    def open_index(self, index_name, db_cache_size=DEFAULT_CACHE_SIZE_STR):
        """
        Returns an index with the specified name opened in read mode with
        the specified db_cache_size.

        See :ref:`performance-cache` for details on setting cache sizes.
        The cache size may be either an integer specifying the size in
        bytes or a string with the optional suffixes K, M or G.

        :param index_name: the name of the index to open
        :type index_name: str
        :param db_cache_size: the size of the cache on the index
        :type db_cache_size: str or int.
        """
        self.verify_open(WT_READ)
        index = Index(self, index_name)
        if not index.exists():
            raise IOError("index '" + index_name + "' not found")
        index.set_db_cache_size(db_cache_size)
        index.open("r")
        return index

class Index(Database):
    """
    An index is an auxiliary table that sorts the rows according to
    column values.
    """
    DB_PREFIX = "index_"
    def __init__(self, table, name):
        Database.__init__(self, table.get_homedir(), self.DB_PREFIX + name)
        self.__name = name
        self.__table = table
        self.__key_columns = []
        self.__bin_widths = []

    def get_name(self):
        """
        Return the name of this index.
        """
        return self.__name

    def get_colspec(self):
        """
        Returns the column specification for this index.
        """
        s = ""
        for c, w in zip(self.__key_columns, self.__bin_widths):
            s += c.get_name()
            if w != 0.0:
                s += "[{0}]".format(w)
            s += "+"
        return s[:-1]

    # Methods for accessing the key_columns
    def key_columns(self):
        """
        Returns the list of key columns.
        """
        return list(self.__key_columns)

    def bin_widths(self):
        """
        Returns the list of bin widths in this index.
        """
        return list(self.__bin_widths)

    def add_key_column(self, key_column, bin_width=0):
        """
        Adds the specified key_column to the list of key_columns we are indexing.
        """
        self.__key_columns.append(key_column)
        self.__bin_widths.append(bin_width)

    def _create_ll_object(self, build):
        """
        Returns a new instance of _wormtable.Index using ether the build or
        permanent locations for the db.
        """
        filename = self.get_db_path().encode()
        if build:
            filename = self.get_db_build_path().encode()
        cols = [c.get_position() for c in self.__key_columns]
        i = _wormtable.Index(self.__table.get_ll_object(), filename,
                cols, self.get_db_cache_size())
        i.set_bin_widths(self.__bin_widths)
        return i

    def get_metadata(self):
        """
        Returns an ElementTree instance describing the metadata for this
        Index.
        """
        d = {"version":INDEX_METADATA_VERSION}
        root = ElementTree.Element("index", d)
        key_columns = ElementTree.Element("key_columns")
        root.append(key_columns)
        for j in range(len(self.__key_columns)):
            c = self.__key_columns[j]
            w = self.__bin_widths[j]
            if c.get_type() == WT_INT | c.get_type() == WT_UINT:
                w = int(w)
            d = {
                "name":c.get_name(),
                "bin_width":str(w),
            }
            element = ElementTree.Element("key_column", d)
            key_columns.append(element)
        return ElementTree.ElementTree(root)

    def set_metadata(self, tree):
        """
        Sets up this Index to reflect the metadata in the specified xml
        ElementTree.
        """
        root = tree.getroot()
        if root.tag != "index":
            # Should have a custom error for this.
            raise ValueError("invalid xml")
        version = root.get("version")
        if version is None:
            # Should have a custom error for this.
            raise ValueError("invalid xml")
        supported_versions = ["0.1-alpha", INDEX_METADATA_VERSION]
        if version not in supported_versions:
            raise ValueError("Unsupported index metadata version - rebuild required.")
        xml_key_columns = root.find("key_columns")
        for xmlcol in xml_key_columns.getchildren():
            if xmlcol.tag != "key_column":
                raise ValueError("invalid xml")
            name = xmlcol.get("name")
            col = self.__table.get_column(name)
            bin_width = float(xmlcol.get("bin_width"))
            self.__key_columns.append(col)
            self.__bin_widths.append(bin_width)

    def build(self, progress_callback=None, callback_rows=100):
        """
        Builds this index. If progress_callback is not None, invoke this
        calback after every callback_rows have been processed.
        """
        llo = self.get_ll_object()
        if progress_callback is not None:
            llo.build(progress_callback, callback_rows)
        else:
            llo.build()

    def open(self, mode):
        """
        Opens this index in the specified mode. Mode must be one of
        'r' or 'w'.

        :param: mode: The mode to open the index in.
        :type: mode: str
        """
        self.__table.verify_open(WT_READ)
        Database.open(self, mode)

    def close(self):
        """
        Closes this Index.
        """
        try:
            Database.close(self)
        finally:
            self.__key_columns = []
            self.__bin_widths = []

    def keys(self):
        """
        Returns an iterator over all the keys in this Index in sorted
        order.
        """
        self.verify_open(WT_READ)
        dvi = _wormtable.IndexKeyIterator(self.get_ll_object())
        for k in dvi:
            yield self.ll_to_key(k)


    def min_key(self, *k):
        """
        Returns the smallest key greater than or equal to the specified
        prefix.
        """
        if len(k) == 0:
            key = k
        else:
            key = self.key_to_ll(k)
        v = self.get_ll_object().get_min(key)
        return self.ll_to_key(v)

    def max_key(self, *k):
        """
        Returns the largest index key less than the specified prefix.
        """
        if len(k) == 0:
            key = k
        else:
            key = self.key_to_ll(k)
        v = self.get_ll_object().get_max(key)
        return self.ll_to_key(v)

    def counter(self):
        """
        Returns an IndexCounter object for this index. This provides an efficient
        method of iterating over the keys in the index.
        """
        self.verify_open(WT_READ)
        return IndexCounter(self)


    def cursor(self, columns, start=KEY_UNSET, stop=KEY_UNSET):
        """
        Returns a cursor over the rows in the table in the order defined
        by this index, retrieving only the specified columns. Rows are
        returned as Tuple objects, with the value for each column in the same
        position as the corresponding column in the list of columns provided.

        The columns specified may be either :class:`Column` instances, integers
        or strings. If an integer is provided, the column
        at the specified position is used and if a string is provided, the column
        with the specified identifier is used. These may be mixed arbitrarily.

        The *start* and *stop* arguments are analogous to the built in
        :func:`range` function. The cursor will iterate over all rows such that
        the *start* <= key < stop. Note that *start* is inclusive, and
        *stop* is exclusive. These parameters may specified values for up to
        n columns, for an n column index. For multiple values, a tuple must
        be provided; a single value of the relevant type is considered to
        be the same as a singleton tuple consisting of this value.

        :param columns: columns to retrieve from the table
        :type columns: sequence of column identifiers
        :param start: the key prefix that is less than or equal to all keys
            in returned rows.
        :param stop: the key prefix that is greater than all keys in returned
            rows.
        """
        self.verify_open(WT_READ)
        col_pos = [c.get_position() for c in
                self.__table.translate_columns(columns)]
        iri = _wormtable.IndexRowIterator(self.get_ll_object(), col_pos)
        # We use the KEY_UNSET protocol here because None is actually a valid
        # key when we have a single column index
        if start != KEY_UNSET:
            key = self.key_to_ll(start)
            iri.set_min(key)
        if stop != KEY_UNSET:
            key = self.key_to_ll(stop)
            iri.set_max(key)
        return iri


    def key_to_ll(self, v):
        """
        Translates the specified tuple as a key to a tuple ready to
        for use in the low-level API.
        """
        cols = self.__key_columns
        if len(cols) == 1:
            l = [v]
        else:
            n = len(v)
            l = [None for j in range(n)]
            for j in range(n):
                l[j] = v[j]
                if isinstance(l[j], str):
                    l[j] = l[j].encode()
        return tuple(l)

    def ll_to_key(self, v):
        """
        Translates the specified value from the low-level key value to its
        high-level equivalent.
        """
        ret = v
        cols = self.__key_columns
        if len(cols) == 1:
            ret = v[0]
        return ret


class IndexCounter(collections.Mapping):
    """
    A counter for Indexes, based on the collections.Counter class. This class
    is a dictionary-like object that represents a mapping of the distinct
    keys in the index to the number of times those keys appear.
    """
    def __init__(self, index):
        self.__index = index

    def __getitem__(self, key):
        k = self.__index.key_to_ll(key)
        return self.__index.get_ll_object().get_num_rows(k)

    def __iter__(self):
        dvi = _wormtable.IndexKeyIterator(self.__index.get_ll_object())
        for v in dvi:
            yield self.__index.ll_to_key(v)

    def __len__(self):
        n = 0
        dvi = _wormtable.IndexKeyIterator(self.__index.get_ll_object())
        for v in dvi:
            n += 1
        return n

