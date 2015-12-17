# BrowseVCF
BrowseVCF is a web-based application and workflow to quickly prioritise disease-causative variants in VCF files.

### Installation
##### *Windows-specific notes*
Download the .zip file on the release page, unzip it somewhere, and double-click on launcher-windows.bat in the web directory. This version is shipped with a stripped-down WinPython v2.7.10, and pre-compiled wormtable modules. Tested on Windows 7.

##### *GNU/Linux-specific notes*
Download the .tar.gz file at the bottom of this page, extract it and launch the application. You should have a Python 2.7 install along with the wormtable package (>= 0.1.5a2).

### Usage as stand-alone web application
BrowseVCF used as web application is composed of four steps:
1. Upload and pre-process your input .vcf or .vcf.gz file
2. Create indexes for one or more annotation fields of interest
3. Filter variants according to different criteria/fields/cutoffs
4. Export results and query history

### Usage as command-line tool
The folder "scripts" contains the key set of Python scripts that perform the same actions of the web application. To see the list of required and optional parameters of any script, simply write:

```sh
$ python script_name.py --help
```

### Development
Want to contribute? Great! Simply report a new issue on GitHub or write an email to:
- Silvia Salatino: silvia (AT) well (DOT) ox (DOT) ac (DOT) uk
- Varun Ramraj: varun (AT) well (DOT) ox (DOT) ac (DOT) uk

### License
BrowseVCF is available under the [GPL v3] license.

[//]: # (These are reference links used in the body of this note and get stripped out when the markdown processor does its job. There is no need to format nicely because it shouldn't be seen. Thanks SO - http://stackoverflow.com/questions/4823468/store-comments-in-markdown-syntax)


   [GPL v3]: http://www.gnu.org/licenses/gpl-3.0.en.html



