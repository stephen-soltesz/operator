#!/usr/bin/env python

## NOTE:
##     purpose is to parse the output of lshw
##     arguments include:
#           all=x     -- number of matches to return
#           section=x -- section to return

import sys
import re

def main():
    if len(sys.argv) < 4:
        print "provide all args"
        sys.exit(1)

    all=0
    section="cpu"
    filename=None
    l=0
    hit=0

    for arg in sys.argv:
        if "all" in arg:
            f=arg.split("=")
            all=int(f[1])
        elif "section" in arg:
            f=arg.split("=")
            section=f[1]
        else:
            filename=arg

    if filename is None or all == 0:
        print "bad arguments"
        sys.exit(1)

    for line in open(filename, 'r'):
        pat = "^\W*-"+section+".*"
        header_pat = "^\W*-.*"
        if re.search(header_pat, line):
            #print l, all, hit, section
            l=0
            if hit > 0:
                hit=0
                all=all-1
                if all<=0: sys.exit(0)

        if re.search(pat, line) and "DISABLED" not in line:
            if l==0: l=1
            hit=1

        if l==1:
            print line.replace(" \t\n", '')[:-1]
if __name__ == "__main__":
    try:
        main()
    except IOError:
        sys.exit(0)
