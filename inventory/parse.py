#!/usr/bin/env python

import sys
from optparse import OptionParser
import xml.etree.ElementTree as ET

def usage():
    return """
    
    """
def print_element(config, node):
    attribs = ",".join([str(k)+"="+str(v) for (k,v) in node.attrib.iteritems() ])
    if config.print_tagname:
        print node.tag, 
    value = ""
    if node.text is not None:
        value = node.text.strip()
    print value, attribs

def main():
    parser = OptionParser(usage=usage())
    parser.add_option("", "--children", dest="print_children", action="store_true",
                          default=False,
                          help="print children of matching elemnts")
    parser.add_option("", "--tag", dest="print_tagname", action="store_true",
                          default=False,
                          help="prefix element data with tagname")
    (config, args) = parser.parse_args()

    if len(args) < 2:
        parser.print_help()
        sys.exit(1)

    filename = args[0]
    xpath = args[1]

    tree = ET.parse(filename)


    for node in tree.getroot().findall(xpath):
        print_element(config, node)
        if not config.print_children:
            continue
        for child in node.getchildren():
            if child.tag == "node":
                break
            print_element(config, child)

if __name__ == "__main__":
    main()

#print root.tag
#print root.attrib
#for child in root:
#    print child.tag, child.attrib, child.text

#for neighbor in root.iter(sys.argv[2]):
#    print neighbor.attrib

## Nodes with claimed='true' that have a 'description' child
# $ ./parse.py mlab1.nuq0t.xml ".//description/..[@claimed='true']"

## 'description' nodes that are children of nodes with claimed='true'
# $ ./parse.py mlab1.nuq0t.xml ".//*[@claimed='true']/description" 
#
## All 'nodes' of class=processor with vendor children
# $ ./parse.py ./mlab1.lca01.xml "./node/node/vendor/..[@class='processor']" 

