#!/usr/bin/env python
import os
import sys
import glob
import argparse
import platform
try:
    import psutil
except ImportError:
    pass #move on quietly
import multiprocessing
from subprocess import Popen, PIPE
from datetime import datetime

# Cross-platform stuff... let's first figure out what we're running on
current_os = platform.system()

# Agnostic paths based on platform
WIN_PLATFORM_NONFREE = False
TOOLPATH = "/usr/local/bin/"  # on Unix systems, vcf2wt etc. are not in /usr/bin

if 'windows' in current_os.lower():
  WIN_PLATFORM_NONFREE = True
  TOOLPATH = os.getcwd() + "\\win_tools\\"
  TOOLPATH = TOOLPATH.replace('\\', '\\\\')

if current_os.lower() == 'linux':
    import wormtable as wt
else:
    import wormtable_other as wt

################################################################################
# This script allows the user to convert the pre-processed vcf file to several
# wormtables. Individual wormtables are created for the fields of interest and
# for a few fields by default (CHROM+POS, REF+ALT).
################################################################################

# Global variables
out_folder = ""

def parse_args():
  """
  Parse the input arguments.
  """

  parser = argparse.ArgumentParser()
  parser.add_argument('-i', dest = 'inp_file', required = True,
                      help = 'input pre-processed file [.vcf|.vcf.gz]')
  parser.add_argument('-o', dest = 'out_folder', required = True,
                      help = 'output folder [existing]')
  parser.add_argument('-t', dest = 'num_cores', required = False,
                      help = 'Number of cores to use (set to 0 for all CPUs)')
  parser.add_argument('-f', dest = 'user_fields', required = True,
                      help = 'fields of interest [comma-separated]')

  args = parser.parse_args()
  return args

def check_input_file(file_name):
  """
  Make sure that the input file's path is properly defined.
  """

  if not os.path.exists(file_name):
    sys.stderr.write("\nFile named '" + file_name + "' does not exist.\n")
    sys.exit(1)
  return file_name

def check_output_file(folder_name):
  """
  If folder_name does not already exist, create it.
  """

  if not os.path.exists(os.path.normpath(folder_name)):
    os.makedirs(os.path.normpath(folder_name))
  return folder_name

def create_single_field_schemas(schema_file, user_fields):
  """
  Using the general .xml schema, create a new schema for each field listed in
  user_fields, which will be used to generate the corresponding wormtables.
  It also creates two special wormtables, one with CHROM+POS and another with
  REF+ALT, to facilitate queries.
  """

  # create single field schemas
  xml = open(schema_file)
  header = xml.readline()      #<?xml version="1.0" ?>
  header += xml.readline()     #<schema address_size="2" version="0.3">
  header += xml.readline()     #  <!--Edit this candidate schema to suit...
  header += xml.readline()     #  <columns>
  rowid_line = xml.readline()  #    <column description="Primary key column"...
  footer = '\n'.join(['  </columns>',
                      '</schema>']) + '\n'
  for line in xml:
    try:
      fname = ""
      if line != rowid_line:
        field_name = line.split(' name=')[1].split(' num_elements=')[0].strip('"')
        if field_name == 'CHROM':
          chrom_line = line
        elif field_name == 'POS':
          pos_line = line
        elif field_name == 'REF':
          ref_line = line
        elif field_name == 'ALT':
          alt_line = line
        if field_name in set(user_fields.split(',')):
          fname = out_folder + '/schema_' + field_name + '.xml'
          new_xml = open(fname, 'w')
          new_xml.write(header)
          new_xml.write(rowid_line)
          new_xml.write(line)
          new_xml.write(footer)
          new_xml.close()
    except IndexError:
      pass
    except IOError, e:
      print fname, sys.exc_info()[1]
  xml.close()
  # create double field schema CHROM+POS
  new_xml = open(out_folder + '/schema_CHROM+POS.xml', 'w')
  new_xml.write(header)
  new_xml.write(rowid_line)
  new_xml.write(chrom_line)
  new_xml.write(pos_line)
  new_xml.write(footer)
  new_xml.close()
  # create double field schema REF+ALT
  new_xml = open(out_folder + '/schema_REF+ALT.xml', 'w')
  new_xml.write(header)
  new_xml.write(rowid_line)
  new_xml.write(ref_line)
  new_xml.write(alt_line)
  new_xml.write(footer)
  new_xml.close()
  return

def make_chunks(l, n):
  """
  Yield successive n-sized chunks from a list l.
  """

  for i in xrange(0, len(l), n):
    yield l[i:i+n]

def create_one_wormtable(schema_path, inp_file, out_file):
  """
  Create a single wormtable database from the input file and an .xml schema.
  """

  cachesize = '16G '
  if WIN_PLATFORM_NONFREE:
      cachesize = '4G ' # to deal with BDB error...

  runargs = '-q --schema ' + schema_path + ' --cache-size=' + cachesize + \
            inp_file + ' ' + out_file
  #run vcf2wt as a library function, no system calls
  try:
      wt.vcf2wt_main(runargs.split())
  except:
      raise #return quietly

  # add row index for this wormtable
  # supersedes add_all_rowid_indexes() and add_one_rowid_index()
  # doing it here means we avail of the thread/process that is already spawned
  # sys.stderr.write('Indexing %s\n' % (out_file,))
  runargs = 'add -q --cache-size=' + cachesize + out_file + ' row_id'
  wt.wtadmin_main(runargs.split())

  return

def create_all_wormtables(inp_file, out_folder, cores = 0):
  """
  Convert the input .vcf file into several .wt (wormtables), one per field.
  To speed up the process, use multi-threading on all available cores of the
  current machine.
  """
  all_schema_files = []

  allfiles = glob.glob(out_folder + '/*.xml')
  allwts = glob.glob(out_folder + '/*.wt')

  #only add filenames if a corresponding wt does not already exist!
  for fname in allfiles:
    if fname.replace('schema_', '').replace('.xml', '.wt') not in allwts:
      all_schema_files.append(fname)

  # use all cores if default value is set
  #update: use psutil if possible
  allcores = 1
  try:
    allcores = psutil.NUM_CPUS
  except AttributeError: #windows has a function call
    allcores = psutil.cpu_count()
  except:
    try:
      allcores = multiprocessing.cpu_count()
    except NotImplementedError:
      pass

  if cores == 0 or cores > allcores:
    cores = allcores
  # if core count < 0, then set it to one core
  elif cores < 0:
    cores = 1
  chunks = make_chunks(all_schema_files, cores)
  results = list()

  for chunk in chunks:
    pool = multiprocessing.Pool(processes=cores)
    for schema_path in chunk:
      out_file = schema_path.replace('schema_', '')
      out_file = out_file.replace('.xml', '.wt')
      results.append(pool.apply_async(create_one_wormtable,
                     [schema_path, inp_file, out_file]))
    pool.close()
    try:
      for r in results:
        r.get()
    except Exception, exc:
        raise #raise the exception to the caller

    pool.join()

  return all_schema_files

def add_one_rowid_index(wt_path):
  """
  Add the 'row_id' index to the wormtable wt_path.
  """

  cachesize = '16G '
  if WIN_PLATFORM_NONFREE:
      cachesize = '4G ' # to deal with BDB error...
      wt_path = wt_path.replace('\\', '\\\\')
  # run wtadmin as a library function, no system calls
  runargs = 'add -q --cache-size=' + cachesize + wt_path + ' row_id'
  wt.wtadmin_main(runargs.split())
  return

def add_all_rowid_indexes(inp_file, out_folder, all_schema_files, cores = 0):
  """
  Add the 'row_id' index to all wormtables in out_folder. To speed up the
  process, use multi-threading on all available cores of the current machine.
  """

  all_wormtables = []
  for wtname in all_schema_files:
    all_wormtables.append(wtname.replace('schema_', '').replace('.xml', '.wt'))

  # use all cores if default value is set
  #update: use psutil if possible
  allcores = 1
  try:
    allcores = psutil.NUM_CPUS
  except AttributeError: #windows has a function call
    allcores = psutil.cpu_count()
  except:
    try:
      allcores = multiprocessing.cpu_count()
    except NotImplementedError:
      pass

  if cores == 0 or cores > allcores:
    cores = allcores
  # if core count < 0, then set it to one core
  elif cores < 0:
    cores = 1
  chunks = make_chunks(all_wormtables, cores)
  results = list()
  for chunk in chunks:
    pool = multiprocessing.Pool(processes=cores)
    for wt_path in chunk:
      results.append(pool.apply_async(add_one_rowid_index, [wt_path]))
    pool.close()
    try:
      for r in results:
        r.get()
    except Exception, exc:
      print exc
      sys.exit(1)
    pool.join()
  return

def add_chrompos_index(out_folder):
  """
  Add the 'CHROM+POS' index to the wormtable 'CHROM+POS.wt'.
  """

  # Turning this off for now, since it's not much overhead
  # and needs to be created the first time, which this check won't allow!
  #if os.path.exists(os.path.join(out_folder, 'CHROM+POS.wt')):
  #  return

  cachesize = '16G '
  divider = '/'
  if WIN_PLATFORM_NONFREE:
      cachesize = '4G ' # to deal with BDB error...
      out_folder = out_folder.replace('\\', '\\\\')
      divider = '\\\\'
  #run wtadmin as a library function, no system calls!
  #for now, force this index to run each time...
  runargs = 'add -q --force --cache-size=' + cachesize + out_folder + divider + \
            'CHROM+POS.wt CHROM+POS'
  wt.wtadmin_main(runargs.split())
  return

def get_total_variant_count(out_folder):
  """
  Get the total (initial) number of variants.
  """

  tbl = wt.open_table(os.path.join(out_folder, 'schema.wt'))
  return len(tbl)

def script02_api_call(i_file, o_folder, u_fields, n_cores):
  """
  API call for web-based and other front-end services, to avoid a system call
  and a new Python process.
  """

  global out_folder
  t1 = datetime.now()
  inp_file = check_input_file(i_file)
  out_folder = check_output_file(o_folder)

  user_fields = u_fields
  schema_file = out_folder + '/' + 'schema.xml'

  create_single_field_schemas(schema_file, user_fields)

  all_schema_files = create_all_wormtables(inp_file, \
                            out_folder, cores = int(n_cores))

  #add_all_rowid_indexes(inp_file, out_folder, \
  #                        all_schema_files, cores = int(n_cores))

  add_chrompos_index(out_folder)
  t2 = datetime.now()
  return

def main():
  """
  Main function.
  """

  args = parse_args()
  script02_api_call(args.inp_file, args.out_folder, args.user_fields,
                    args.num_cores)

if __name__ == '__main__':
  main()
