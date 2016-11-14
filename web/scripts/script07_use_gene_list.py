#!/usr/bin/env python
import os
import sys
import glob
import argparse
from datetime import datetime

import platform

if platform.system().lower() == 'darwin':
    os.environ['PYTHONPATH'] = '%s/osx_libs:$PYTHONPATH' % os.getcwd()
    
import wormtable as wt

################################################################################
# This script allows the user to filter variants in a vcf file based on one or 
# more genes of interest. Genes can be provided as a comma-separated string or 
# as a text file, with one gene per line. The query can be either positive (keep
# variants annotated to any of the input genes) or negative (keep variants not
# annotated to any of the input genes).
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
  parser.add_argument('-g', dest = 'genes_to_query', required = True,
                      help = 'genes of interest [comma-sep. string or file ' +
                      'path]')
  parser.add_argument('-f', dest = 'field_name', required = True,
                      help = 'field where gene names have to be searched')
  parser.add_argument('-n', dest = 'negative_query', required = True,
                      help = 'is this a negative query? [True or False]')
  parser.add_argument('-p', dest = 'previous_results', required = False,
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

def store_genes(genes_to_query):
  """
  Store all input gene names in a set. If the path of genes_to_query does not
  exist, it will treat genes_to_query as a string.
  """

  genes = set()
  # genes_to_query is a text file
  if os.path.exists(genes_to_query):
    f = open(genes_to_query)
    for line in f:
      genes.add(line.strip('\n'))
    f.close()
  # genes_to_query is a comma-separated string
  else:
    genes = set(genes_to_query.split(','))
  return genes

def get_variants_assoc_to_gene_set_from_previous_results(inp_folder, genes,
  field_name, negative_query, previous_results):
  """
  Open the field_name wormtable (assumed to be named 'inp_folder/field_name.wt')
  within inp_folder and return a set of all row IDs where at least one gene from
  genes is found. Use ids from previous_results as starting point to further
  filter the data and to make it faster.
  If negative_query is True, only variants NOT containing any of the input genes
  in field_name will be returned; if False, viceversa (positive query is run).
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
  all_ids = set()
  pos_ids = set()
  # NOTE: it assumes the wormtable has only two columns: 'row_id' and field_name
  row_id_idx = 0
  field_name_idx = 1
  for row in index.cursor(['row_id', field_name]):
    if row[row_id_idx] in ids_to_check:
      all_ids.add(row[row_id_idx])
      for value in row[field_name_idx].split(','):
        for gene in genes:
          if value.find(gene) != -1:
            pos_ids.add(row[row_id_idx])
            break
  # close table and index
  table.close()
  index.close()
  # if "negative_query" is True, return all row IDs which are not in "pos_ids"
  if negative_query == 'True':
    neg_ids = all_ids - pos_ids
    return neg_ids
  elif negative_query == 'False':
    return pos_ids

def get_variants_assoc_to_gene_set(inp_folder, genes, field_name,
  negative_query):
  """
  Open the field_name wormtable (assumed to be named 'inp_folder/field_name.wt')
  within inp_folder and return a set of all row IDs where at least one gene from
  genes is found.
  If negative_query is True, only variants NOT containing any of the input genes
  in field_name will be returned; if False, viceversa (positive query is run).
  """

  # open wormtable for the field of interest
  table = wt.open_table(inp_folder + '/' + field_name + '.wt',
          db_cache_size='4G')
  all_ids = set()
  pos_ids = set()
  # NOTE: it assumes the wormtable has only two columns: 'row_id' and field_name
  row_id_idx = 0
  field_name_idx = 1
  for row in table.cursor(['row_id', field_name]):
    all_ids.add(row[row_id_idx])
    for value in row[field_name_idx].split(','):
      for gene in genes:
        if value.find(gene) != -1:
          pos_ids.add(row[row_id_idx])
          break
  # close table
  table.close()
  # if "negative_query" is True, return all row IDs which are not in "pos_ids"
  if negative_query == 'True':
    neg_ids = all_ids - pos_ids
    return neg_ids
  elif negative_query == 'False':
    return pos_ids

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

def script07_api_call(i_folder, o_file, genes_to_query, field_name,
  negative_query, previous_results = None):
  """
  API call for web-based and other front-end services, to avoid a system call
  and a new Python process.
  """

  t1 = datetime.now()
  inp_folder = check_input_file(i_folder)
  out_file = check_output_file(o_file)
  negative_query = str(negative_query).lower()
  if negative_query.startswith('t'):
      negative_query = 'True'
  else:
      negative_query = 'False'
  genes = store_genes(genes_to_query)
  if previous_results != None:
    ids = get_variants_assoc_to_gene_set_from_previous_results(inp_folder,
          genes, field_name, negative_query, previous_results)
  else:
    ids = get_variants_assoc_to_gene_set(inp_folder, genes, field_name,
          negative_query)
  retrieve_variants_by_rowid(inp_folder, ids, out_file)
  t2 = datetime.now()
  sys.stderr.write('%s\n' % str(t2 - t1))
  return

def main():
  """
  Main function.
  """
  args = parse_args()
  script07_api_call(args.inp_folder, args.out_file, args.genes_to_query,
                    args.field_name, args.negative_query, args.previous_results)

if __name__ == '__main__':
  main()

