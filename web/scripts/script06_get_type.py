#!/usr/bin/env python
import os
import sys
import glob
import argparse
from datetime import datetime

import platform
if platform.system().lower() == 'linux':
    import wormtable as wt
else:
    import wormtable_other as wt


################################################################################
# This script allows the user to filter variants in a vcf file based the variant
# type (one of: SNPs, InDels, MNPs).
################################################################################

def parse_args():
  """
  Parse the input arguments.
  """

  parser = argparse.ArgumentParser()
  parser.add_argument('-i', dest = 'inp_folder', required = True,
                      help = 'input folder containing the several wormtables')
  parser.add_argument('-o', dest = 'out_file', required = True,
                      help = 'output file [.txt]')
  parser.add_argument('-t', dest = 'var_type', required = True,
                      help = 'variant type [one of: SNPs, InDels, MNPs]')
  parser.add_argument('-p', dest = 'previous_results', required=False,
                      help = 'previously saved results from another query ' +
                      '[.txt]')
  args = parser.parse_args()
  return args

def check_input_file(folder_name):
  """
  Make sure that the input file's path is properly defined.
  """

  if not os.path.exists(folder_name):
    sys.stderr.write("\nFolder named '" + folder_name + "' does not exist.\n")
    sys.exit()
  return folder_name

def check_output_file(file_name):
  """
  Make sure that the input file's path does not already exist.
  """

  if os.path.exists(file_name):
    sys.stderr.write("\nFile named '" + file_name + "' already exists.\n")
    sys.exit()
  return file_name

def get_variants_of_given_type_from_previous_results(inp_folder, var_type,
  previous_results):
  """
  Open the REF+ALT wormtable (assumed to be named 'inp_folder/REF+ALT.wt')
  within inp_folder and return a set of all row IDs correspoding to var_type.
  Use ids from previous_results as starting point to further filter the data and
  to make it faster.
  """

  # extract row IDs to check from previous_results (which is a file path) and
  # store them in a set; NOTE: it assumes previous_results has a 1-line header,
  # is tab-separated and row_id is the left-most field!
  ids_to_check = set()
  f = open(previous_results)
  header = True
  for line in f:
    if header:
      header = False
    else:
      ids_to_check.add(int(line.split('\t')[0]))
  f.close()
  # open REF+ALT wormtable
  table = wt.open_table(inp_folder + '/REF+ALT.wt', db_cache_size='4G')
  index = table.open_index('row_id')
  # retrieve rows matching 'var_type'
  ids = set()
  # NOTE: it assumes the wormtable has three columns: 'row_id', 'REF', 'ALT'
  row_id_idx = 0
  ref_idx = 1
  alt_idx = 2
  if var_type == 'SNPs':
    for row in index.cursor(['row_id', 'REF', 'ALT']):
      if row[row_id_idx] in ids_to_check:
        for alt in row[alt_idx].split(','):
          if len(row[ref_idx]) == 1 and len(alt) == 1:
            ids.add(row[row_id_idx])
            break
  elif var_type == 'InDels':
    for row in index.cursor(['row_id', 'REF', 'ALT']):
      if row[row_id_idx] in ids_to_check:
        for alt in row[alt_idx].split(','):
          if len(row[ref_idx]) != len(alt):
            ids.add(row[row_id_idx])
            break
  elif var_type == 'MNPs':
    for row in index.cursor(['row_id', 'REF', 'ALT']):
      if row[row_id_idx] in ids_to_check:
        for alt in row[alt_idx].split(','):
          if len(row[ref_idx]) > 1 and len(row[ref_idx]) == len(alt):
            ids.add(row[row_id_idx])
            break
  else:
    sys.stderr.write("\nVariant type not properly defined.\n")
    sys.exit()
  # close table and index
  table.close()
  index.close()
  return ids

def get_variants_of_given_type(inp_folder, var_type):
  """
  Open the REF+ALT wormtable (assumed to be named 'inp_folder/REF+ALT.wt')
  within inp_folder and return a set of all row IDs correspoding to var_type.
  """

  # open REF+ALT wormtable
  table = wt.open_table(inp_folder + '/REF+ALT.wt', db_cache_size='4G')
  # retrieve rows matching 'var_type'
  ids = set()
  # NOTE: it assumes the wormtable has three columns: 'row_id', 'REF', 'ALT'
  row_id_idx = 0
  ref_idx = 1
  alt_idx = 2
  if var_type == 'SNPs':
    for row in table.cursor(['row_id', 'REF', 'ALT']):
      for alt in row[alt_idx].split(','):
        if len(row[ref_idx]) == 1 and len(alt) == 1:
          ids.add(row[row_id_idx])
          break
  elif var_type == 'InDels':
    for row in table.cursor(['row_id', 'REF', 'ALT']):
      for alt in row[alt_idx].split(','):
        if len(row[ref_idx]) != len(alt):
          ids.add(row[row_id_idx])
          break
  elif var_type == 'MNPs':
    for row in table.cursor(['row_id', 'REF', 'ALT']):
      for alt in row[alt_idx].split(','):
        if len(row[ref_idx]) > 1 and len(row[ref_idx]) == len(alt):
          ids.add(row[row_id_idx])
          break
  else:
    sys.stderr.write("\nVariant type not properly defined.\n")
    sys.exit()
  # close table
  table.close()
  return ids

def retrieve_variants_by_rowid(inp_folder, ids, out_file):
  """
  Use the row IDs in ids to query the complete wormtable (containing all variant
  fields) and return all the information about the filtered variants.
  """

  # open table and load indices
  table = wt.open_table(inp_folder + '/schema.wt', db_cache_size='4G')
  index = table.open_index('row_id')
  # retrieve the rows using the 'row_id' field and write the results in out_file
  col_names = [col.get_name() for col in table.columns()]
  row_id_idx = col_names.index('row_id')
  out = open(out_file, 'w')
  out.write('\t'.join(col_names) + '\n')
  for row in index.cursor(col_names):
    if row[row_id_idx] in ids:
      to_write = list()
      for value in row:
        try:  # value is a number (int or float)
          to_write.append(int(value))
        except TypeError, e:  # value is a tuple
          if value is not None:
            to_write.append(','.join([str(x) for x in value]))
          else:
            to_write.append(None)
        except ValueError, e:  # value is a string
          to_write.append(value)
        except:
          to_write.append(None)
      out.write('\t'.join([str(x) for x in to_write]) + '\n')
  out.close()
  # close table and index
  table.close()
  index.close()
  return

def script06_api_call(i_folder, o_file, var_type, previous_results = None):
  """
  API call for web-based and other front-end services, to avoid a system call
  and a new Python process.
  """

  t1 = datetime.now()
  inp_folder = check_input_file(i_folder)
  out_file = check_output_file(o_file)
  if previous_results != None:
    ids = get_variants_of_given_type_from_previous_results(inp_folder, var_type,
          previous_results)
  else:
    ids = get_variants_of_given_type(inp_folder, var_type)
  retrieve_variants_by_rowid(inp_folder, ids, out_file)
  t2 = datetime.now()
  print t2 - t1
  return

def main():
  """
  Main function.
  """

  args = parse_args()
  script06_api_call(args.inp_folder, args.out_file, args.var_type, args.previous_results)

if __name__ == '__main__':
  main()

