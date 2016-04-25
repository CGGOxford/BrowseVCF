Welcome to BrowseVCF version 2.6
================================

BrowseVCF is a web-based application and workflow to quickly prioritise disease-causative variants in VCF files.

# Table of Contents
1. [Requirements and Installation](#requirements-and-installation)  
1.1 [For Windows users](#for-windows-users)  
1.2 [For GNU Linux users](#for-gnu-linux-users)  
1.3 [For Mac users](#for-mac-users)  
2. [Usage as standalone web application](#usage-as-stand-alone-web-application)  
3. [Usage as command line tool](#usage-as-command-line-tool)  

### 1. Requirements and Installation

##### 1.1 *For Windows users*
Download the zip file (`browseVCF_win7_vX.X.zip`) from the [release page], unzip it somewhere, and double-click on `launcher-windows.bat` in the `web` directory. 

##### 1.2 *For GNU Linux users*
1. The latest versions of CentOS, Fedora, Redhat and Ubuntu come with Python 2.7 out of the box. 
If it's not installed, download Python from `https://www.python.org/`.

2. Install pip
`wget https://bootstrap.pypa.io/get-pip.py`
`python get-pip.py`

3. Install dependencies 
`sudo pip install psutil`
`sudo pip install cherrypy`
`sudo pip install cherrypy-cgiserver`

4. Install Berkeley DB
`sudo apt-get install libdb-dev` (Ubuntu/Debian) or `yum install libdb-devel` (Red Hat/Fedora)

5. Install Wormtable
`sudo apt-get install python-dev` (Ubuntu/Debian) or `yum install python-devel` (Red Hat/Fedora)
`wget https://pypi.python.org/packages/source/w/wormtable/wormtable-0.1.5a2.tar.gz`
`tar -xvf wormtable-0.1.5a2.tar.gz`
`cd wormtable-0.1.5a2`
`sudo python setup.py install`

6. Download BrowseVCF (substitute X.X with latest version)
`wget https://github.com/BSGOxford/BrowseVCF/archive/vX.X.tar.gz`
`tar -xvf vX.X.tar.gz`

##### 1.3 *For Mac OS users*
Download the OSX-specific .tar.gz file on the [release page], unzip it somewhere, and run `launcher-osx.sh` from a Terminal within the `web` directory. This version is shipped with a stripped-down Python v2.7.11 compiled on OSX, along with pre-compiled wormtable and BerkeleyDB modules. Tested on OSX El Capitan.

Alternatively, to compile from source, please follow the instructions below.

1. The latest versions of Mac OS X come with Python 2.7 out of the box. 
If it's not installed, download Python from `https://www.python.org/`.

2. Install pip
`wget https://bootstrap.pypa.io/get-pip.py`
`python get-pip.py`

3. Install dependencies 
`sudo pip install psutil`
`sudo pip install cherrypy`
`sudo pip install cherrypy-cgiserver`

4. Install Berkeley DB
`sudo port install db53`

5. Install Wormtable
`wget https://pypi.python.org/packages/source/w/wormtable/wormtable-0.1.5a2.tar.gz`
`tar -xvf wormtable-0.1.5a2.tar.gz`
`cd wormtable-0.1.5a2`
`CFLAGS=-I/opt/local/include/db53 LDFLAGS=-L/opt/local/lib/db53/ python setup.py build`
`sudo python setup.py install`

6. Download BrowseVCF (substitute X.X with latest version)
`wget https://github.com/BSGOxford/BrowseVCF/archive/vX.X.tar.gz`
`tar -xvf vX.X.tar.gz`

### 2. Usage as standalone web application
BrowseVCF used as web application is composed of four steps:

1. Upload and pre-process your input .vcf or .vcf.gz file
2. Create indexes for one or more annotation fields of interest
3. Filter variants according to different criteria/fields/cutoffs
4. Export results and query history

A more detailed tutorial is provided as PDF from the [release page], together with a VCF sample file. The PDF tutorial shows how to apply the different filters on the VCF sample file with the most frequenctly used queries.

### 3. Usage as command line tool
The folder "scripts" contains the key set of Python scripts that perform the same actions of the web application. To see the list of required and optional parameters of any script, simply write:

```sh
$ python script_name.py --help
```

### 4. Contact and Contribute
Want to contribute? Great! Simply report a new issue on GitHub or write an email to:
- Silvia Salatino: silvia (AT) well (DOT) ox (DOT) ac (DOT) uk
- Varun Ramraj: varun (AT) well (DOT) ox (DOT) ac (DOT) uk

### 5. License
BrowseVCF is available under the [GPL v3] license.


[//]: # (These are reference links used in the body of this note and get stripped out when the markdown processor does its job. There is no need to format nicely because it shouldn't be seen.

   [GPL v3]: http://www.gnu.org/licenses/gpl-3.0.en.html
   [release page]: https://github.com/BSGOxford/BrowseVCF/releases

