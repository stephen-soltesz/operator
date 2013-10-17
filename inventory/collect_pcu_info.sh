#!/usr/bin/env bash

source collect_common.sh

if test -z "$1" ; then
    echo ""
    echo "Usage:    collect_pcu_info.sh <site.host>"
    echo ""
    echo "  This script collects system info from the DRACs on M-Lab servers."
    echo "  If supported by 'drac.py getsysinfo' the output is saved to:"
    echo "       sysinfo/\$SITE/\$HOST.raw"
    echo "       sysinfo/\$SITE/\$HOST.parsed"
    echo "  Finally, this script updates the MLabInventory spreadsheet."
    echo ""
    exit 1
fi

# NOTE: setup relative paths to m-lab/operator/tools
TOOLSDIR=$( readlink -f $( dirname $0 )/../tools )

SITEHOST=$1
FORCE_UPDATE=$2

SITE=$( echo $SITEHOST | tr '.' ' ' | awk '{print $1}' )
HOST=$( echo $SITEHOST | tr '.' ' ' | awk '{print $2}' )

mkdir -p sysinfo/$SITE/
HOST_SITE=${HOST}.${SITE}
RAW_SYSINFO="sysinfo/$SITE/$HOST.raw"
PARSED_SYSINFO="sysinfo/$SITE/$HOST.parsed"

# NOTE: check that the file is missing or a forced test
if ! test -f $RAW_SYSINFO || test -n "$FORCE_UPDATE" ; then
    tmpfile=$( mktemp )
    $TOOLSDIR/drac.py getsysinfo $HOST_SITE > $tmpfile
    if grep -qE "DRAC SYSINFO|IMM SYSINFO|HPILO SYSINFO" $tmpfile 2> /dev/null ; then
        err_echo "Saving sysinfo to $RAW_SYSINFO"
        mv $tmpfile $RAW_SYSINFO
    else
        err_echo "Failed to get info for $RAW_SYSINFO"
        rm -f $tmpfile
        exit 1
    fi
fi

# NOTE: At this point we are guaranteed that:
#     1) $RAW_SYSINFO exists
#     2) $RAW_SYSINFO contains some model 'hints'

# NOTE: So, begin parsing based on model hints
if grep -qE "DRAC SYSINFO" $RAW_SYSINFO 2> /dev/null ; then
    format_raw_drac $RAW_SYSINFO > $PARSED_SYSINFO

elif grep -qE "IMM SYSINFO" $RAW_SYSINFO 2> /dev/null ; then
    format_raw_imm $RAW_SYSINFO > $PARSED_SYSINFO

elif grep -qE "HPILO SYSINFO" $RAW_SYSINFO 2> /dev/null ; then
    format_raw_hpilo $RAW_SYSINFO > $PARSED_SYSINFO

else
    err_echo "Error: $RAW_SYSINFO was collected, but"
    err_echo "       contains unrecognized system information."
    err_echo "Error: Is this a new type or model?"
    exit 1
fi

# NOTE: print parsed data
cat $PARSED_SYSINFO
