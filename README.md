# doku2tiddly
A Python tool to migrate DokuWiki to TiddlyWiki

## About
This script will process the plain text storage files DokuWiki uses, translating that content to the TiddlyWiki syntax style and outputting an importable json. Additionally it has the ability to organize that content in a format more applicable to TiddlyWiki by creating a Table of Contents and developing top level categories based on the DokuWiki organization of pages.

## Getting Started

doku2tiddly is run from the command line and needs a DokuWiki pages directory as it's only parameter.
DokuWiki typically stores it's content files in wiki/data/pages/

If exporting an existing DokuWiki to an empty TiddlyWiki, it is recommended to also generate a Table of Contents node [--createtoc].

### Usage
Typically `doku2tiddly.py -dir pages --createtoc --capitalizetitles --savestats`

```
usage: doku2tiddly.py [--help] [--dir DIR] [--tocname TOCNAME] [--verbose]
                      [--ignore IGNORE] [--capitalizetitles]
                      [--outfile OUTFILE] [--createtoc]
                      [--syntaxtest SYNTAXTEST] [--savestats]

DESCRIPTION: Export dokuwiki data to importable tiddlywiki json

optional arguments:
  --help, -h            		show this help message and exit
  --dir DIR, -d DIR     		folder to search in; by default current folder
  --tocname TOCNAME, -t TOCNAME		table of contents tag name; by defaul "TOC"
  --verbose, -v         		create a Table of Contents node
  --ignore IGNORE, -i IGNORE		page name to ignore
  --capitalizetitles    		capitalize page titles
  --outfile OUTFILE, -o OUTFILE		output filename (json)
  --createtoc, -c       		create a Table of Contents node
  --syntaxtest INFILE, -x INFILE 	run syntax test on file
  --savestats, -s       		create a node storing these stats/settings
```

### Syntax Test
doku2tiddly has regex matches for most patterns. You can run a syntax match test with the [--syntatest] parameter, which expects a syntax file as it's input. This will print the translation result to console. A basic syntax file can be found here [Syntax Example](tests/syntax_dokuwiki.txt)

For Example `doku2tiddly.py --syntaxtest tests/syntax_dokuwiki.txt`

### Requirements

* doku2tiddly requires Python 3 to run. See python.org for install info.
* doku2tiddly has been tested with Python 3.6 and 3.7
* Tested with syntax style up to DokuWiki 2018-04-22a "Greebo"
* Tested import logic and syntax style for TiddlyWiki 5.1.17
