#!/usr/bin/env python3

import argparse
import sys
import re
import os
import fnmatch
import json
import datetime
from string import capwords


# pattern map for dokuwiki to tiddlywiki syntax
dict_dokuout = {
    'codeblocks':           [r'(?s)<code\s?(.*?)>(.+?)<\/code>',    r'\n```\1\2```'],
    'monospace':            [r'\'{2}(.+?)\'{2}',                    r'`\1`'],
    'noformat':             [r'(?s)%%(.+?)%%',                      r'\n```\1```'],
    'nowiki':               [r'(?s)<nowiki>(.+?)<\/nowiki>',        r'\n```\1```'],
    'filetag':              [r'(?s)<file\s?(.*?)>(.+?)<\/file>',    r'\n```\1\2```'],
    'h1':                   [r'={6}(.+?)={6}',                      r'!\1'],
    'h2':                   [r'={5}(.+?)={5}',                      r'\n!!\1'],
    'h3':                   [r'={4}(.+?)={4}',                      r'\n!!!\1'],
    'h4':                   [r'={3}(.+?)={3}',                      r'\n!!!!\1'],
    'h5':                   [r'={2}(.+?)={2}',                      r'\n!!!!!\1'],
    'tableheader':          [r'\^.+?',                              r'|!'],
    'tableheaderclose':     [r'(?m)\^$',                            r'|'],
    'bold':                 [r'\*{2}(.+?)\*{2}',                    '\'\'\\1\'\''],
    #'italic':              [r'//(.+?)//',                          r'//\1//'], #same
    #'underline':           [r'__(.+?)__',                          r'__\1__'], #same
    'strikethrough':        [r'<del>(.+?)</del>',                   r'~~\1~~'],
    'superscript':          [r'<sup>(.+?)</sup>',                   r'^^\1^^'],
    'subscript':            [r'<sub>(.+?)</sub>',                   r',,\1,,'],
    'horizontalrule':       [r'(?m)^\s?\-{4}$',                     r'\n---\n'],
    'ulistlvl1':            [r'(?m)^ {2}\*',                        r'*'],
    'ulistlvl2':            [r'(?m)^ {4}\*',                        r'**'],
    'ulistlvl3':            [r'(?m)^ {6}\*',                        r'***'],
    'olistlvl1':            [r'(?m)^ {2}\-',                        r'#'],
    'olistlvl2':            [r'(?m)^ {4}\-',                        r'##'],
    'olistlvl3':            [r'(?m)^ {6}\-',                        r'###'],
    'imagetag':             [r'\{{2}.*?:?(.+?):(.+?\.\w{3,4}).*?\}{2}',   r'[img [img/\1/\2]]'],
    #'imagetagwithsize':    [r'\{{2}.*?:?(.+?):(.+?\.\w{3,4})(\?.*?\&?(\d{2,4}).*?)?.*?\}{2}',   r'[img [img/\1/\2]]'],
}


def translatePage(dictmap, text):
    # translate existing page text to new format and return
    # walk through dictionary and do regex substitute (find/replace)
    # key0 for search pattern, key1 for replacement
    for key in dictmap:
        text = re.sub(dictmap[key][0], dictmap[key][1], text)
    return text


def checkTitleCollision(title, tag, tocname):
    global _dupecount
    global _catcollisioncount
    global _pageslist
    global _actionlog

    # collision check for duplicate title names. TiddlyWiki requires unique title names
    for node in _pageslist:
        if node['title'].lower() == title.lower():
            # if current title matches an existing node title
            _dupecount += 1
            if tag == tocname:
                # if current tag is TOC, then this is a main level category node and needs name priority
                # name priority is needed on a category node so that child nodes aren't orphaned by the name change
                _catcollisioncount += 1

                # if existing node is also a main level category node, we have a problem...
                # bandaid check to avoid blasting an existing top level category name
                if node['tags'] == tocname:
                    sys.exit("ERROR: unreconcilable naming collision on - {} vs {}".format(node['title'], title))

                # rename existing node to make way for current node
                # only if it's not a category itself
                node['title'] = node['title'] + ' (' + node['tags'] + ')'

                # log this action
                _actionlog.append('WARNING: Top Level Naming Failure on {}. '
                                 'Renaming previous node to {}'.format(title, node['title']))
                if config.verbose:
                    print(_actionlog[-1])
            else:
                # this current node is not a main category
                # so we'll rename it by appending it's parent category to it's title
                title = title + ' (' + tag + ')'
                # log this action
                _actionlog.append('WARNING: duplicate title detected, renaming to {}'.format(title))
                if config.verbose:
                    print(_actionlog[-1])

    return title


def createPageNode(created, tag, title, text, addfields=None):
    # create a node from components
    # tag will be the parent category
    global _nodecount

    title = checkTitleCollision(title, tag, config.tocname)

    package = {
        "created":  created,
        "tags":     tag,
        "title":    title,
        "text":     text
    }

    # if additional fields passed in, add those to the package
    if addfields is not None:
        for key, val in addfields.items():
            package[key] = val

    _nodecount += 1

    return package


def createCategoryNode(currentpath, rootdir, currentdir, created, tocname):
    # check if dir above this one is search root (cfg.dir)
    # if not, its a sub/sub and needs a tag other than TOC
    # or were still in root and it should get TOC
    parenttag = os.path.dirname(currentpath).split('/')[-1]
    if parenttag == rootdir or currentdir == rootdir:
        parenttag = tocname

    categorytext = '<div class="tc-table-of-contents">\n    <<toc "' + currentdir + '" "sort[title]">>\n</div>'

    return createPageNode(created, parenttag, currentdir, categorytext, {"toc-link": "no"})


def createTocNode(created, tocname):
    # return a preloaded Table of Contents node
    tag = "$:/tags/SideBar"
    text = "<div class=\"tc-table-of-contents\">\n    <<toc-selective-expandable '" + \
           tocname + "' \"sort[title]\">>\n</div>"
    fields = {
        "caption": "Contents",
        "list-after": "$:/core/ui/SideBar/Open"
    }

    return createPageNode(created, tag, tocname, text, fields)


def createStatsNode(created):
    # return a node with export info
    # +1 nodecount for self
    tag = "stats"
    title = "Stats - Export: " + created
    text = ("\"\"\" ''Date:'' " + created + "\n" +
            "''Files Processed:'' " + str(_filecount) + "\n" +
            "''Nodes Created:'' " + str(_nodecount+1) + "\n" +
            "''Duplicate Titles Renamed:'' " + str(_dupecount) + "\n" +
            "''Resolved Category Title Collisions:'' " + str(_catcollisioncount) + "\n" +
            "''Export Arguments:'' " + " ".join(sys.argv[1:]) +
            "\"\"\"\n\n ''Action Log:''\n\n```\n" + "\n".join(_actionlog) + "\n```"
            )

    return createPageNode(created, tag, title, text)


def writeOut(alist, outfile):
    # encode and write out.
    with open(outfile, "w") as f:
        # indent prettifies the output for readability
        f.write(json.dumps(alist, indent=4))


def processFiles(cfg):
    global _filecount
    global _pageslist

    # timestamp used as createddate for all pages in this batch.
    # Follows tiddlyWiki format YYMMDD24MMSS + 3dig millisecond, 000 here for simplicity
    timestamp = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S') + '000'

    if cfg.createtoc:
        # create a table of contents tiddler
        _pageslist.append(createTocNode(timestamp, cfg.tocname))

    for path, dirs, files in os.walk(os.path.abspath(cfg.dir)):
        # get current directory for use as parent tag
        # also used to create main category name
        parentdir = os.path.basename(path)

        # create a Parent Tiddler for the following pages
        _pageslist.append(createCategoryNode(path, cfg.dir, parentdir, timestamp, cfg.tocname))

        for filename in fnmatch.filter(files, "*.txt"):
            # process all txt files in current directory

            # check for ignored file names
            if cfg.ignore and filename == cfg.ignore:
                continue

            pagetitle = os.path.splitext(filename)[0]
            # check for Capitalize Titles flag
            if cfg.capitalizetitles:
                pagetitle = capwords(pagetitle)

            filepath = os.path.join(path, filename)

            # log file process action
            _actionlog.append("Processing File: {}".format(os.path.join(os.path.relpath(path), filename)))
            # if verbose mode print to console
            if cfg.verbose:
                print(_actionlog[-1])

            # get entire contents of file and close
            with open(filepath) as f:
                pagedata = f.read()

            # translate existing page text to new format
            pagedata = translatePage(dict_dokuout, pagedata)

            # add current page to pagesList
            _pageslist.append(createPageNode(timestamp, parentdir, pagetitle, pagedata))

            # update filecount
            _filecount += 1

    if cfg.savestats:
        # create an export stats node
        _pageslist.append(createStatsNode(timestamp))

    # encode to json and write to file
    writeOut(_pageslist, cfg.outfile)


def syntaxTest(dictmap, syntaxfile):
    # used to syntax test a single file
    with open(syntaxfile) as f:
        subject = f.read()

    print(translatePage(dictmap, subject))


if __name__ == '__main__':
    # load up command line argument parser
    parser = argparse.ArgumentParser(description='DESCRIPTION: Export dokuwiki data to importable tiddlywiki json',
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog='USAGE: {0} -d <pages directory> [-t <table of contents name>'
                                            ' --createtoc --capitalizetitles --savestats]'
                                     .format(os.path.basename(sys.argv[0])))

    parser.add_argument('--dir', '-d',
                        help='folder to search in; by default current folder', default='.')

    parser.add_argument('--tocname', '-t',
                        help='table of contents tag name; by default "TOC"', default='TOC')

    parser.add_argument('--verbose', '-v',
                        help='Create a Table of Contents node', action='store_true', default=False)

    parser.add_argument('--ignore', '-i',
                        help='page name to ignore', default='start.txt')

    parser.add_argument('--capitalizetitles',
                        help='capitalize page titles', action='store_true', default=False)

    parser.add_argument('--outfile', '-o',
                        help='output filename (json)', default='tiddler_import.json')

    parser.add_argument('--createtoc', '-c',
                        help='create a Table of Contents node', action='store_true', default=False)

    parser.add_argument('--syntaxtest', '-x',
                        help='run syntax test on file', default='')

    parser.add_argument('--savestats', '-s',
                        help='create a node storing these stats/settings', action='store_true', default=False)

    config = parser.parse_args(sys.argv[1:])

    # create list of all pages
    _pageslist = []

    # create log of actions
    _actionlog = []

    # global event counters
    _filecount = 0
    _nodecount = 0
    _dupecount = 0
    _catcollisioncount = 0

    # main function
    if config.syntaxtest:
        syntaxTest(dict_dokuout, config.syntaxtest)
    else:
        processFiles(config)

        print('\nOK: Export Complete. JSON file ready.')
        print("--: {} Files Processed".format(_filecount))
        print("--: {} Nodes Created".format(_nodecount))
        print("--: {} Duplicate Titles Renamed".format(_dupecount))
        print("--: {} Resolved Category Naming Collisions".format(_catcollisioncount))


# NOTES
# ----
# Regex
# ----
# Specials . ^ $ * + ? { } [ ] \ | ( )
# .* any character 0 or more times
# .+ any char 1 or more times
# ? disables greedy mode; match occurs asap instead of as late as possible by default
# () backreference carried forward with \1, \2, etc..
# re.DOTALL flag indicates match any character including newlines
# postfix (?s) indicates DOTALL
# inline flags should be at the start of the pattern ie (?m)
# ----
# DokuWiki
# ----
# start.txt is default section page name
# ----
# TiddlyWiki
# ----
# toc-link: no - flags a tiddler as non clickable in TOC, but does expand it's tree. Used for main categories
# TiddlyWiki uses Title as a unique identifier. A duplicate Title in a new tiddler will overwrite the previous
# display quirk in tw requires newline before code block if not under a heading text,
# display quirk in tw headings need newline above except h1

# TO DO
# ----
# 1. duplicate safety check bug where a sub dir (2nd level+ category) could collide with naming of a top level category
