#!/usr/bin/env bash

source collect_host_common.sh

if test -z "$1" ; then
    echo ""
    echo "Usage:    collect_host_all.sh run"
    echo ""
    echo "  This script collects system info from all M-Lab hosts"
    echo "  And, updates a spreadsheet."
    echo ""
    exit
fi
shift   # remove 'run'

# NOTE: setup relative paths to m-lab/operator/tools
TOOLSDIR=$( readlink -f $( dirname $0 )/../tools )
HOSTLIST=hostlist.txt
TABLENAME=hardware
set -x

if ! test -f $HOSTLIST ; then
    $TOOLSDIR/plcquery.py --action get --type node \
              --filter "hostname=*.measurement-lab.org" \
              --fields "hostname" > $HOSTLIST
fi
HOST_LIST=`cat $HOSTLIST`

# NOTE: update ssh keys before using them.
$TOOLSDIR/get-mlab-sshconfig.py --update --config

# NOTE: create the spreadsheet if not already present.
./gspreadsheet.py --table $TABLENAME --create --columns $COLUMNS

for hostname in $HOST_LIST ; do 
    HOST=$( echo $hostname | tr '.' ' ' | awk '{print $1}' )
    SITE=$( echo $hostname | tr '.' ' ' | awk '{print $2}' )

    echo $SITE.$HOST
    if ! ./gspreadsheet.py --table $TABLENAME \
             --update \
             --row $SITE.$HOST \
             --results "./collect_host_info.sh %(site.machine)s" ; then
        echo "Error: spreadsheet update failed for $SITE.$HOST"
        exit 1
    fi
done

