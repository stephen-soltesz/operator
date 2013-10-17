#!/usr/bin/env bash

source collect_common.sh

if test -z "$1" ; then
    echo ""
    echo "Usage:    collect_pcu_all.sh run"
    echo ""
    echo "  This script collects system info from all PCUs (DRAC, HPiLO, IMM)."
    echo "  Finally, this script updates the MLabInventory spreadsheet."
    echo ""
    echo "Usage:    collect_pcu_all.sh run <site.host>"
    echo ""
    echo "  Just download given hostname, and update the MLabInventory."
    echo ""
    exit
fi
shift   # remove 'run'

# NOTE: setup relative paths to m-lab/operator/tools
TOOLSDIR=$( readlink -f $( dirname $0 )/../tools )
PCULIST=pculist.txt
TABLENAME=drac

if ! test -f $PCULIST ; then
    $TOOLSDIR/plcquery.py --action get --type pcu \
              --filter "hostname=*.measurement-lab.org" \
              --fields "hostname" > $PCULIST
fi
HOST_LIST=`cat $PCULIST`

set -x

# NOTE: create the spreadsheet if not already present.
$TOOLSDIR/gdict.py --table $TABLENAME --create --columns $PCU_COLUMNS

for hostname in $HOST_LIST ; do 
    HOST=$( echo $hostname | tr '.' ' ' | awk '{print $1}' )
    SITE=$( echo $hostname | tr '.' ' ' | awk '{print $2}' )
    mkdir -p sysinfo/$SITE/

    echo $SITE.$HOST
    if ! $TOOLSDIR/gdict.py --table $TABLENAME \
             --key $SITE_$HOST \
             --update \
             --results "./collect_pcu_info.sh {$SITE_MACHINE}" ; then
        echo "Error: spreadsheet update failed for $SITE_$HOST"
        exit 1
    fi
done

