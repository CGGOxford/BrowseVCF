Welcome to BrowseVCF version 2.7
================================

BrowseVCF is a web-based application and workflow to quickly prioritise 
disease-causative variants in VCF files.

# Table of Contents
1. [Requirements and Installation](#1-requirements-and-installation)  
  1. [For Windows users](#i-for-windows-users)  
  2. [For GNU Linux users](#ii-for-gnu-linux-users)  
  3. [For Mac OS users](#iii-for-mac-os-users)  
2. [Usage as standalone web application](#2-usage-as-standalone-web-application)  
3. [Usage as command line tool](#3-usage-as-command-line-tool)  
4. [Contact and Contribute](#4-contact-and-contribute)  
5. [License](#5-license)

### 1. Requirements and Installation

##### i. *For Windows users*
Download the zip file (`browseVCF_win7_vX.X.zip`) from the [release page], 
unzip it in a path that **does not contain spaces**, and double-click on 
`launcher-windows.bat` in the `web` directory. 

##### ii. *For GNU Linux users*
Download the GNU/Linux-specific .tar.gz file on the [release page], unzip it 
in a path that **does not contain spaces**, and run `launcher-gnu.sh` from a 
Terminal within the `web` directory. This version is shipped with a 
stripped-down Python v2.7 compiled on GNU/Linux, along with pre-compiled 
wormtable and BerkeleyDB modules. Tested on Ubuntu version 14.04.

Alternatively, to compile from source, please follow the instructions below.

1) The latest versions of CentOS, Fedora, Redhat and Ubuntu come with 
Python 2.7 out of the box. 
If it's not installed, download Python from `https://www.python.org/`.

2) Install pip  
`wget https://bootstrap.pypa.io/get-pip.py`  
`python get-pip.py`

3) Install dependencies  
`sudo pip install psutil`  
`sudo pip install cherrypy`  
`sudo pip install cherrypy-cgiserver`  

4) Install Berkeley DB  
`sudo apt-get install libdb-dev` (Ubuntu/Debian) or `yum install libdb-devel` 
(Red Hat/Fedora)

5) Install Wormtable  
`sudo apt-get install python-dev` (Ubuntu/Debian) or `yum install python-devel` 
(Red Hat/Fedora)  
`sudo pip install wormtable`

6) Download BrowseVCF (substitute X.X with latest version)  
`wget https://github.com/BSGOxford/BrowseVCF/archive/vX.X.tar.gz`  
`tar -xvf vX.X.tar.gz`

##### iii. *For Mac OS users*
Download the OSX-specific .tar.gz file on the [release page], unzip it 
in a path that **does not contain spaces**, and run `launcher-osx.sh` from a 
Terminal within the `web` directory. This version is shipped with a 
stripped-down Python v2.7 compiled on OSX, along with pre-compiled wormtable 
and BerkeleyDB modules. Tested on OSX El Capitan.

Alternatively, to compile from source, please follow the instructions below.

1) The latest versions of Mac OS X come with Python 2.7 out of the box. 
If it's not installed, download Python from `https://www.python.org/`.

2) Install pip  
`wget https://bootstrap.pypa.io/get-pip.py`  
`python get-pip.py`

3) Install dependencies  
`sudo pip install psutil`  
`sudo pip install cherrypy`  
`sudo pip install cherrypy-cgiserver`

4) Install Berkeley DB  
`sudo port install db53`

5) Install Wormtable  
`sudo pip install wormtable`  
`CFLAGS=-I/opt/local/include/db53 LDFLAGS=-L/opt/local/lib/db53/ python setup.py build`  
`sudo python setup.py install`

6) Download BrowseVCF (substitute X.X with latest version)  
`wget https://github.com/BSGOxford/BrowseVCF/archive/vX.X.tar.gz`  
`tar -xvf vX.X.tar.gz`

### 2. Usage as standalone web application
BrowseVCF used as web application is composed of four steps:

1) Upload and pre-process your input .vcf or .vcf.gz file  
2) Create indexes for one or more annotation fields of interest  
3) Filter variants according to different criteria/fields/cutoffs  
4) Export results and query history

A more detailed **tutorial** is provided as PDF from the [release page], 
together with a VCF sample file. The PDF tutorial shows how to apply the 
different filters on the VCF sample file with the most frequenctly used queries.

### 3. Usage as command line tool
The folder `scripts` inside `web` contains the key set of Python scripts that 
perform the same actions of the web application:

- `script01_preprocess.py` -> Essential. Must be executed as first.  
It preprocess the input vcf file in order to be compatible with wormtable.
- `script02_convert_to_wt.py` -> Essential. Must be executed as second.  
It creates the indexes that will be used to query the annotation fields of 
interest.
- `script03_filter_field.py` -> Discretionary. Corresponds to filter A of the web 
application.  
Performs queries on a given field of interest any of the following operators: 
'greater_than', 'less_than', 'equal_to', 'contains_keyword', 'is_absent', 
'is_present'.
- `script04_select_genotype.py` -> Discretionary. Corresponds to filter B of the 
web application.  
Filters variants based on their genotype in one or more samples.
- `script05_region_of_interest.py` -> Discretionary. Corresponds to filter C of 
the web application.  
Keeps only those variants located within the input region of interest.
- `script06_get_type.py` -> Discretionary. Corresponds to filter D of the web 
application.  
Allows to select variants of a given type ('SNPs', 'InDels', 'MNPs').
- `script07_use_gene_list.py` -> Discretionary. Corresponds to filter E of the 
web application.  
Keeps only variants annotated with one of the gene names/IDs provided as input.

Scripts 01 and 02 must be run in this specific order before being able to run 
any of the other scripts (03, 04, 05, 06, 07).

To see the list of required and optional parameters of any script, simply write:

```sh
$ python script_name.py --help
```

### 4. Contact and Contribute
Want to contribute? Great! Simply report a new issue on GitHub or write an 
email to:
- Silvia Salatino: silvia (AT) well (DOT) ox (DOT) ac (DOT) uk
- Varun Ramraj: varun (AT) well (DOT) ox (DOT) ac (DOT) uk

### 5. License
BrowseVCF is available under the [GPL v3] license.

   [GPL v3]: http://www.gnu.org/licenses/gpl-3.0.en.html
   [release page]: https://github.com/BSGOxford/BrowseVCF/releases

