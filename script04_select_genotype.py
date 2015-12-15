#!/usr/bin/env python
import os
import sys
import glob
import argparse
import wormtable as wt
from datetime import datetime

################################################################################
# This script allows the user to filter variants in a vcf file based on a
# specific genotype for one, several or all samples present in the input file.
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
  parser.add_argument('-g', dest = 'genotype', required = True,
                      help = 'genotype [one of: het, hom]')
  parser.add_argument('-s', dest = 'samples', required = True,
                      help = "samples [either 'all' or comma-separated list" +
                             " of sample IDs]")
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

def get_sample_names(inp_folder, samples):
  """
  Identify the wormtables that need to be queried.
  """

  samples_list = list()
  if samples == 'all':
    for wt in glob.iglob(inp_folder + '/*.GT.wt'):
      samples_list.append(wt)
  else:
    for wt in samples.split(','):
      samples_list.append(inp_folder + '/' + wt + '.GT.wt')
  return samples_list

def filter_variants_from_previous_results(inp_folder, genotype, samples_list,
  previous_results):
  """
  Open all wormtables (assumed to be named 'inp_folder/sample_name_GT.wt') in
  inp_folder corresponding to the specified samples and filter or discard
  variants according to the specified genotype. The row_id value of each
  filtered variant is stored in the set ids, which is returned. Use ids from
  previous_results as starting point to further filter the data and to make it
  faster.
  It works also for non-diploid genotypes. Non-informative genotypes (e.g. './.'
  are skipped.
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
  # sample_ids has sample names as keys and id sets as values
  samples_ids = dict()
  for sample in samples_list:
    # open wormtable for the field of interest
    table = wt.open_table(sample, db_cache_size='4G')
    index = table.open_index('row_id')
    # retrieve rows matching genotype in samples_list and store their row_id
    ids = set()
    row_id_idx = 0
    sample_idx = 1
    for row in index.cursor(['row_id',
    os.path.basename(sample).replace('.wt', '')]):
      # only analyse row if row_id is among the ones in ids_to_check
      if row[row_id_idx] in ids_to_check:
        gen = row[sample_idx].replace('/','').replace('|','')
        # note: gen == len(gen)*gen[0] to check if all the characters in a
        # string are the same is even faster than count()!
        if gen == len(gen)*gen[0] and genotype == 'hom' and gen[0] != '.':
          ids.add(row[row_id_idx])
        elif gen != len(gen)*gen[0] and genotype == 'het' and gen[0] != '.':
          ids.add(row[row_id_idx])
    # close table and store results
    table.close()
    index.close()
    samples_ids[sample] = ids
  return samples_ids

def filter_variants(inp_folder, genotype, samples_list):
  """
  Open all wormtables (assumed to be named 'inp_folder/sample_name_GT.wt') in
  inp_folder corresponding to the specified samples and filter or discard
  variants according to the specified genotype. The row_id value of each
  filtered variant is stored in the set ids, which is returned.
  It works also for non-diploid genotypes. Non-informative genotypes (e.g. './.'
  are skipped.
  """

  # sample_ids has sample names as keys and id sets as values
  samples_ids = dict()
  for sample in samples_list:
    # open wormtable for the field of interest
    table = wt.open_table(sample, db_cache_size='4G')
    # retrieve rows matching genotype in samples_list and store their row_id
    ids = set()
    row_id_idx = 0
    sample_idx = 1
    for row in table:
      gen = row[sample_idx].replace('/','').replace('|','')
      # note: gen == len(gen)*gen[0] to check if all the characters in a
      # string are the same is even faster than count()!
      if gen == len(gen)*gen[0] and genotype == 'hom' and gen[0] != '.':
        ids.add(row[row_id_idx])
      elif gen != len(gen)*gen[0] and genotype == 'het' and gen[0] != '.':
        ids.add(row[row_id_idx])
    # close table and store results
    table.close()
    samples_ids[sample] = ids
  return samples_ids

def intersect_ids(samples_ids):
  """
  Keep only those row IDs that are shared between the samples in samples_ids.
  """

  final_ids = set.intersection(*[samples_ids[x] for x in samples_ids])
  return final_ids

def retrieve_variants_by_rowid(inp_folder, final_ids, out_file):
  """
  Use the row IDs in final_ids to query the complete wormtable (containing all
  variant fields) and return all the information about the filtered variants.
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
    if row[row_id_idx] in final_ids:
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

def script04_api_call(i_folder, o_file, genotype, samples,
  previous_results = None):
  """
  API call for web-based and other front-end services, to avoid a system call
  and a new Python process.
  """

  t1 = datetime.now()
  inp_folder = check_input_file(i_folder)
  out_file = check_output_file(o_file)
  samples_list = get_sample_names(inp_folder, samples)
  if previous_results != None:
    samples_ids = filter_variants_from_previous_results(inp_folder, genotype,
                  samples_list, previous_results)
  else:
    samples_ids = filter_variants(inp_folder, genotype, samples_list)
  final_ids = intersect_ids(samples_ids)
  retrieve_variants_by_rowid(inp_folder, final_ids, out_file)
  t2 = datetime.now()
  print t2 - t1
  return

def main():
  """
  Main function.
  """

  args = parse_args()
  script04_api_call(args.inp_folder, args.out_file, args.genotype, args.samples,
                    args.previous_results)

if __name__ == '__main__':
  main()

