#!/usr/bin/env python
import os
import sys
import math
import argparse
from datetime import datetime

import platform

if platform.system().lower() == 'darwin':
    os.environ['PYTHONPATH'] = '%s/osx_libs:$PYTHONPATH' % os.getcwd()
    
import wormtable as wt

################################################################################
# This script allows the user to filter variants in a vcf file based on a
# specific annotation field of interest. The user must define the operator and
# the cutoff that need to be applied to each value in that field.
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
  parser.add_argument('-f', dest = 'field_name', required = True,
                      help = 'name of the field of interest')
  parser.add_argument('-s', dest = 'operator', required = True,
                      help = 'operator [one of: greater_than, less_than, ' +
                             'equal_to, contains_keyword]')
  parser.add_argument('-c', dest = 'cutoff', required = True,
                      help = 'cutoff for the field of interest or ' +
                             'comma-separated string')
  parser.add_argument('-k', dest = 'keep_novalue', required = True,
                      help = 'keep variants with no value at specified field ' +
                      '[True OR False]')
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

def is_number(s):
  """
  Check whether a string is actually an int or a float (e.g. '1234').
  """

  try:
    float(s)
    return True
  except ValueError:
    return False

def filter_variants_from_previous_results(inp_folder, field_name, operator,
  cutoff, keep_novalue, previous_results):
  """
  Open wormtable within inp_folder corresponding to field_name (assumed to be
  named 'inp_folder/field_name.wt') and filter or discard variants according to
  the specified cutoff. The row_id value of each filtered variant is stored in
  the set ids, which is returned. Use ids from previous_results as starting
  point to further filter the data and to make it faster.
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
  # open wormtable for the field of interest
  table = wt.open_table(inp_folder + '/' + field_name + '.wt',
                        db_cache_size='4G')
  index = table.open_index('row_id')
  # retrieve rows passing the cutoff for field_name and store their row_id
  ids = set()
  # NOTE: it assumes the wormtable has only two columns: 'row_id' and field_name
  row_id_idx = 0
  field_name_idx = 1
  for row in index.cursor(['row_id', field_name]):
    # only analyse row if row_id is among the ones in ids_to_check
    if row[row_id_idx] in ids_to_check:
      # the type of the field value for the current row is 'NoneType', empty,
      # or 'nan'
      if row[field_name_idx] is None or row[field_name_idx] == '':
        if keep_novalue == 'True':
          ids.add(row[row_id_idx])
        else:
          pass
      # the type of the field value for the current row is 'str'
      elif isinstance(row[field_name_idx], str):
        if operator == 'greater_than' or operator == 'less_than':
          # special case: NUM/NUM (which is recognised as string by wormtable)
          # solution: we check that the ratio NUM/NUM is >,<,= cutoff
          for value in row[field_name_idx].split(','):
            if value == '' or value == 'nan':
              if keep_novalue == 'True':
                ids.add(row[row_id_idx])
                break
            elif value.find('/') != -1:
              if operator == 'greater_than':
                if float(value.split('/')[0])/float(value.split('/')[1]) > float(cutoff):
                  ids.add(row[row_id_idx])
                  break
              elif operator == 'less_than':
                if float(value.split('/')[0])/float(value.split('/')[1]) < float(cutoff):
                  ids.add(row[row_id_idx])
                  break
            else:
              sys.stderr.write('\nError: ' + operator + ' incompatible with' +
                               ' field type (string).\n')
              sys.exit()
        elif operator == 'equal_to':
          for value in row[field_name_idx].split(','):
            if value == '' or value == 'nan':
              if keep_novalue == 'True':
                ids.add(row[row_id_idx])
                break
            # special case: NUM/NUM (which is recognised as string by wormtable)
            # solution: we check that the ratio NUM/NUM is >,<,= cutoff
            elif value.find('/') != -1:
              if float(value.split('/')[0])/float(value.split('/')[1]) == float(cutoff):
                ids.add(row[row_id_idx])
                break
            elif value == cutoff:
              ids.add(row[row_id_idx])
              break
        elif operator == 'contains_keyword':
          for value in row[field_name_idx].split(','):
            if value == '' or value == 'nan':
              if keep_novalue == 'True':
                ids.add(row[row_id_idx])
                break
            for keyword in set(cutoff.split(',')):
              if value.find(keyword) != -1:
                ids.add(row[row_id_idx])
                break
      # the type of the field value for the current row is 'tuple'
      elif isinstance(row[field_name_idx], tuple):
        if operator == 'greater_than':
          for value in row[field_name_idx]:
            if math.isnan(value):
              if keep_novalue == 'True':
                ids.add(row[row_id_idx])
                break
            elif value > float(cutoff):
              ids.add(row[row_id_idx])
              break
        elif operator == 'less_than':
          for value in row[field_name_idx]:
            if math.isnan(value):
              if keep_novalue == 'True':
                ids.add(row[row_id_idx])
                break
            elif value < float(cutoff):
              ids.add(row[row_id_idx])
              break
        elif operator == 'equal_to':
          for value in row[field_name_idx]:
            if math.isnan(value):
              if keep_novalue == 'True':
                ids.add(row[row_id_idx])
                break
            elif value == float(cutoff):
              ids.add(row[row_id_idx])
              break
        elif operator == 'contains_keyword':
          for value in row[field_name_idx]:
            if math.isnan(value):
              if keep_novalue == 'True':
                ids.add(row[row_id_idx])
                break
            for keyword in set(cutoff.split(',')):
              if value.find(keyword) != -1:
                ids.add(row[row_id_idx])
                break
      # the type of the field value for the current row is 'int' or 'float'
      # this includes cases of string numbers (e.g. '1234')
      elif is_number(row[field_name_idx]):
        if math.isnan(row[field_name_idx]):
          if keep_novalue == 'True':
            ids.add(row[row_id_idx])
        elif operator == 'greater_than':
          if row[field_name_idx] > float(cutoff):
            ids.add(row[row_id_idx])
        elif operator == 'less_than':
          if row[field_name_idx] < float(cutoff):
            ids.add(row[row_id_idx])
        elif operator == 'equal_to':
          if row[field_name_idx] == float(cutoff):
            ids.add(row[row_id_idx])
        elif operator == 'contains_keyword':
          for keyword in set(cutoff.split(',')):
            if row[field_name_idx].find(keyword) != -1:
              ids.add(row[row_id_idx])
              break
  # close table and index
  table.close()
  index.close()
  return ids

def filter_variants(inp_folder, field_name, operator, cutoff, keep_novalue):
  """
  Open wormtable within inp_folder corresponding to field_name (assumed to be
  named 'inp_folder/field_name.wt') and filter or discard variants according to
  the specified cutoff. The row_id value of each filtered variant is stored in
  the set ids, which is returned.
  """

  # open wormtable for the field of interest
  table = wt.open_table(inp_folder + '/' + field_name + '.wt',
                        db_cache_size='4G')
  # retrieve rows passing the cutoff for field_name and store their row_id
  ids = set()
  # NOTE: it assumes the wormtable has only two columns: 'row_id' and field_name
  row_id_idx = 0
  field_name_idx = 1
  # NOTE: row is a tuple of row_id and field_name
  for row in table.cursor(['row_id', field_name]):
    # the type of the field value for the current row is 'NoneType', empty,
    # or 'nan'
    if row[field_name_idx] is None or row[field_name_idx] == '':
      if keep_novalue == 'True':
        ids.add(row[row_id_idx])
      else:
        pass
    # the type of the field value for the current row is 'str'
    elif isinstance(row[field_name_idx], str):
      if operator == 'greater_than' or operator == 'less_than':
        # special case: NUM/NUM (which is recognised as string by wormtable)
        # solution: we check that the ratio NUM/NUM is >,<,= cutoff
        for value in row[field_name_idx].split(','):
          if value == '' or value == 'nan':
            if keep_novalue == 'True':
              ids.add(row[row_id_idx])
              break
          elif value.find('/') != -1:
            if operator == 'greater_than':
              if float(value.split('/')[0])/float(value.split('/')[1]) > float(cutoff):
                ids.add(row[row_id_idx])
                break
            elif operator == 'less_than':
              if float(value.split('/')[0])/float(value.split('/')[1]) < float(cutoff):
                ids.add(row[row_id_idx])
                break
          else:
            sys.stderr.write('\nError: ' + operator + ' incompatible with' +
                             ' field type (string).\n')
            sys.exit()
      elif operator == 'equal_to':
        for value in row[field_name_idx].split(','):
          if value == '' or value == 'nan':
            if keep_novalue == 'True':
              ids.add(row[row_id_idx])
              break
          # special case: NUM/NUM (which is recognised as string by wormtable)
          # solution: we check that the ratio NUM/NUM is >,<,= cutoff
          elif value.find('/') != -1:
            if float(value.split('/')[0])/float(value.split('/')[1]) == float(cutoff):
              ids.add(row[row_id_idx])
              break
          elif value == cutoff:
            ids.add(row[row_id_idx])
            break
      elif operator == 'contains_keyword':
        for value in row[field_name_idx].split(','):
          if value == '' or value == 'nan':
            if keep_novalue == 'True':
              ids.add(row[row_id_idx])
              break
          for keyword in set(cutoff.split(',')):
            if value.find(keyword) != -1:
              ids.add(row[row_id_idx])
              break
    # the type of the field value for the current row is 'tuple'
    elif isinstance(row[field_name_idx], tuple):
      if operator == 'greater_than':
        for value in row[field_name_idx]:
          if math.isnan(value):
            if keep_novalue == 'True':
              ids.add(row[row_id_idx])
              break
          elif value > float(cutoff):
            ids.add(row[row_id_idx])
            break
      elif operator == 'less_than':
        for value in row[field_name_idx]:
          if math.isnan(value):
            if keep_novalue == 'True':
              ids.add(row[row_id_idx])
              break
          elif value < float(cutoff):
            ids.add(row[row_id_idx])
            break
      elif operator == 'equal_to':
        for value in row[field_name_idx]:
          if math.isnan(value):
            if keep_novalue == 'True':
              ids.add(row[row_id_idx])
              break
          elif value == float(cutoff):
            ids.add(row[row_id_idx])
            break
      elif operator == 'contains_keyword':
        for value in row[field_name_idx]:
          if math.isnan(value):
            if keep_novalue == 'True':
              ids.add(row[row_id_idx])
              break
          for keyword in set(cutoff.split(',')):
            if value.find(keyword) != -1:
              ids.add(row[row_id_idx])
              break
    # the type of the field value for the current row is 'int' or 'float'
    # this includes cases of string numbers (e.g. '1234')
    elif is_number(row[field_name_idx]):
      if math.isnan(row[field_name_idx]):
        if keep_novalue == 'True':
          ids.add(row[row_id_idx])
      elif operator == 'greater_than':
        if row[field_name_idx] > float(cutoff):
          ids.add(row[row_id_idx])
      elif operator == 'less_than':
        if row[field_name_idx] < float(cutoff):
          ids.add(row[row_id_idx])
      elif operator == 'equal_to':
        if row[field_name_idx] == float(cutoff):
          ids.add(row[row_id_idx])
      elif operator == 'contains_keyword':
        for keyword in set(cutoff.split(',')):
          if row[field_name_idx].find(keyword) != -1:
            ids.add(row[row_id_idx])
            break
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

def script03_api_call(i_folder, o_file, f_name, operator, cutoff, keep_novalue,
  prev_results = None):
  """
  API call for web-based and other front-end services, to avoid a system call
  and a new Python process.
  """

  t1 = datetime.now()
  inp_folder = check_input_file(i_folder)
  out_file = check_output_file(o_file)
  field_name = f_name
  # to handle lowercase, uppercase in the fastest way
  keep_novalue = str(keep_novalue).lower()
  if keep_novalue.startswith('t'):
      keep_novalue = 'True'
  else:
      keep_novalue = 'False'
  previous_results = prev_results
  if previous_results != None:
    ids = filter_variants_from_previous_results(inp_folder, field_name, operator,
          cutoff, keep_novalue, previous_results)
  else:
    ids = filter_variants(inp_folder, field_name, operator, cutoff, keep_novalue)
  retrieve_variants_by_rowid(inp_folder, ids, out_file)
  t2 = datetime.now()
  print t2 - t1
  return

def main():
  """
  Main function.
  """

  args = parse_args()
  script03_api_call(args.inp_folder, args.out_file, args.field_name,
                    args.operator, args.cutoff, args.keep_novalue,
                    args.previous_results)

if __name__ == '__main__':
  main()
