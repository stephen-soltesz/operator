#!/usr/bin/env bash

source collect_host_common.sh

if [ -z "$1" ] ; then
    echo ""
    echo "Usage:    collect_host_info.sh <site.host>"
    echo ""
    echo "  First collect raw data and format this raw data."
    echo "  Raw data is saved to hostinfo/SITE/HOST.raw"
    echo ""
    exit 1
fi

# NOTE: setup relative paths to m-lab/operator/tools
TOOLSDIR=$( readlink -f $( dirname $0 )/../tools )
# NOTE: could be parallelized with $TOOLSDIR/fetch.py but, meh.
LSHW_COMMAND="bash -c 'test -f /usr/sbin/lshw || sudo yum install -y lshw && lshw -quiet'"
CPU_COMMAND="bash -c 'cat /proc/cpuinfo'"

SITEHOST=$1
FORCE_UPDATE=$2

SITE=$( echo $SITEHOST | tr '.' ' ' | awk '{print $1}' )
HOST=$( echo $SITEHOST | tr '.' ' ' | awk '{print $2}' )

mkdir -p hostinfo/$SITE/
HOST_SITE=${HOST}.${SITE}
RAW_HOSTINFO="hostinfo/$SITE/$HOST.lshw.raw"
RAW_CPUINFO="hostinfo/$SITE/$HOST.cpu.raw"
PARSED_HOSTINFO="hostinfo/$SITE/$HOST.parsed"

## NOTE: check that the file is missing or a forced test
if ! test -f $RAW_HOSTINFO || test -n "$FORCE_UPDATE" ; then
    tmpfile=$( mktemp )
    err_echo "Trying to collect lshw from $HOST_SITE"
    ssh $HOST_SITE "$LSHW_COMMAND" > $tmpfile
    if ! grep -q "description:" $tmpfile 2> /dev/null ; then
        err_echo "Failed to get info for $RAW_HOSTINFO"
        rm -f $tmpfile
        exit 1
    fi
    err_echo "Saving hostinfo to $RAW_HOSTINFO"
    mv $tmpfile $RAW_HOSTINFO
fi

if ! test -f $RAW_CPUINFO || test -n "$FORCE_UPDATE" ; then
    tmpfile=$( mktemp )
    err_echo "Trying to collect cpuinfo from $HOST_SITE"
    ssh $HOST_SITE "$CPU_COMMAND" > $tmpfile
    if ! grep -q "processor" $tmpfile 2> /dev/null ; then
        err_echo "Failed to get info for $RAW_CPUINFO"
        rm -f $tmpfile
        exit 1
    fi
    err_echo "Saving cpuinfo to $RAW_CPUINFO"
    mv $tmpfile $RAW_CPUINFO
fi

format_raw_host $RAW_HOSTINFO $RAW_CPUINFO > $PARSED_HOSTINFO

# NOTE: print parsed data
cat $PARSED_HOSTINFO
