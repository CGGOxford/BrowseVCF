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
# This script allows the user to filter variants in a vcf file based on one or
# more regions of interest (e.g. for linkage analysis or intergenic variants).
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
  parser.add_argument('-c', dest = 'chrom', required = True,
                      help = 'chromosome')
  parser.add_argument('-s', dest = 'start', required = True,
                      help = 'start position')
  parser.add_argument('-e', dest = 'end', required = True,
                      help = 'end position')
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

def check_start_end(start, end):
  """
  Make sure start is before end and both are positive integers.
  """

  try:
    int(start)
  except ValueError:
    sys.stderr.write("\nStart position is not an integer.\n")
    sys.exit()
  try:
    int(end)
  except ValueError:
    sys.stderr.write("\nEnd position is not an integer.\n")
    sys.exit()
  if start > end:
    sys.stderr.write("\nStart position must be before end position.\n")
    sys.exit()
  if start < 0:
    sys.stderr.write("\nStart position must be positive.\n")
    sys.exit()
  if end < 0:
    sys.stderr.write("\nEnd position must be positive.\n")
    sys.exit()
  return

def get_variants_in_given_regions_from_previous_results(inp_folder, chrom,
    start_pos, end_pos, previous_results):
  """
  Open the CHROM+POS wormtable (assumed to be named 'inp_folder/CHROM+POS.wt')
  within inp_folder and return a set of all row IDs correspoding to the region
  of interest. Use ids from previous_results as starting point to further filter
  the data and to make it faster.
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
  # open CHROM+POS wormtable
  table = wt.open_table(inp_folder + '/CHROM+POS.wt', db_cache_size='4G')
  index = table.open_index('CHROM+POS')
  # retrieve rows matching 'chrom' and whose pos. is between 'start' and 'end'
  ids = set()
  # NOTE: it assumes the wormtable has three columns: 'row_id', 'CHROM', 'POS'
  row_id_idx = 0
  cols = ['row_id', 'CHROM', 'POS']
  for row in index.cursor(cols, start=(chrom, start_pos),
  stop=(chrom, end_pos)):
    if row[row_id_idx] in ids_to_check:
      ids.add(row[row_id_idx])
  # close table and index
  table.close()
  index.close()
  return ids

def get_variants_in_given_regions(inp_folder, chrom, start_pos, end_pos):
  """
  Open the CHROM+POS wormtable (assumed to be named 'inp_folder/CHROM+POS.wt')
  within inp_folder and return a set of all row IDs correspoding to the region
  of interest.
  """

  # open CHROM+POS wormtable
  table = wt.open_table(inp_folder + '/CHROM+POS.wt', db_cache_size='4G')
  index = table.open_index('CHROM+POS')
  # retrieve rows matching 'chrom' and whose pos. is between 'start' and 'end'
  ids = set()
  # NOTE: it assumes the wormtable has three columns: 'row_id', 'CHROM', 'POS'
  row_id_idx = 0
  cols = ['row_id', 'CHROM', 'POS']
  for row in index.cursor(cols, start=(chrom, start_pos),
  stop=(chrom, end_pos)):
    ids.add(row[row_id_idx])
  # close table and index
  table.close()
  index.close()
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

def script05_api_call(i_folder, o_file, chrom, start, end,
  previous_results = None):
  """
  API call for web-based and other front-end services, to avoid a system call
  and a new Python process.
  """
    
  t1 = datetime.now()
  inp_folder = check_input_file(i_folder)
  out_file = check_output_file(o_file)
  # safeguard in case calling function doesn't cast
  start = int(start)
  end = int(end)
  check_start_end(start, end)
  if previous_results != None:
    ids = get_variants_in_given_regions_from_previous_results(inp_folder, chrom,
          start, end, previous_results)
  else:
    ids = get_variants_in_given_regions(inp_folder, chrom, start, end)
  retrieve_variants_by_rowid(inp_folder, ids, out_file)
  t2 = datetime.now()
  print t2 - t1
  return

def main():
  """
  Main function.
  """

  args = parse_args()
  script05_api_call(args.inp_folder, args.out_file, args.chrom, int(args.start),
                    int(args.end), args.previous_results)

if __name__ == '__main__':
  main()

