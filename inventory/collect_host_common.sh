#!/usr/bin/env bash

function err_echo () {
    echo "$@" 1>&2
}

function format_raw_host () {
    local file=$1
    local cpufile=$2

    #cat $file | tr -cd '[:print:]\n' | \
    #    awk '/^\/system1|^\/map1/ { prefix=$1 ; next } 
    #         { print prefix, $1, $2, $3 }' | grep = | grep -v status | sort | \
    #    awk -F= '/system1 number=/      { printf("'$HOST_SERIAL',%s\n", $2); }
    #         /system1 name=/            { printf("'$HOST_MODEL',%s\n", $2); }
    #         /system1\/firmware1 version=/   { printf("'$HOST_BIOS',%s\n", $2); }
    #         /map1 name=/               { printf("'$PCU_MODEL',%s\n", $2); }
    #         /map1\/firmware1 version=/ { printf("'$PCU_FIRMWARE',%s\n", $2); }
    #         /map1\/firmware1 date=/    { printf("'$PCU_UPDATE',%s\n", $2); }'
    #echo $PCU_HARDWARE,

    echo $HOST_SERIAL,$( get_serial $file )
    echo $HOST_MODEL,$( get_model $file )
    echo $PROC_MODEL,$( get_proc_model $cpufile ) 
    PROC_PHY_COUNT=$( get_physical_proc_count $cpufile )
    PROC_RAW_COUNT=$( get_proc_cores_count $cpufile )
    echo $PROC_COUNT,$PROC_PHY_COUNT
    echo $PROC_PER_CORE,$(( $PROC_RAW_COUNT / $PROC_PHY_COUNT ))
    echo $PROC_FREQ,$( get_proc_speed $file )
    echo $PROC_BUS,$( get_proc_bus $file )
    echo $RAM_TOTAL,$( get_ram_total $file )
    echo $RAM_DIMMS,$( get_ram_dimms $file )
    echo $RAM_SPEED,$( get_ram_speed $file )
    echo $NET_MODEL,$( get_net_model $file )
    echo $NET_PORTS,$( get_net_ports $file )
    echo $NET_SPEED,$( get_net_speed $file ) 
    echo $NET_DRIVER,$( get_net_driver $file )
    echo $DISK_TOTAL,$( get_disk_total $file )
    echo $DISK_COUNT,$( get_disk_count $file )
    echo $DISK_DRIVER,$( get_disk_driver $file )

}

function get_value_from () {
    file=$1
    label=$2
    V=`grep -E "$label" $file | sed -e 's/.*=\(.*\)$/\1/g' | tr '\n\r' ' '`
    echo $V
}
#set -x

function get_service_tag () {
    file=$1
    tag=$( get_value_from $file "Service Tag" )
    echo $tag
}
function get_host_model () {
    file=$1
    model=$( get_value_from $file "System Model" )
    revision=$( get_value_from $file "System Revision" )
    if [ -n "$revision" ] ; then
        echo "$model $revision"
    else
        echo "$model"
    fi
}
function get_host_bios () {
    file=$1
    bios=$( get_value_from $file "System BIOS Version" )
    echo $bios
}
function get_drac_firmware () {
    file=$1
    version=$( get_value_from $file "^Firmware Version.*=" )
    build=$( get_value_from $file "^Firmware Build.*=" )
    echo "$version ($build)"
}
function get_drac_hardware () {
    file=$1
    version=$( get_value_from $file "Hardware Version" )
    echo "($version)"
}
function get_drac_update () {
    file=$1
    update=$( get_value_from $file "Last Firmware Update" )
    echo $update
}

function get_drac_model () {
    file=$1
    model=$( get_value_from $file "DNS RAC Name" )
    if grep -q "DRAC 5" $file ; then 
        model="DRAC 5"
    elif grep -q " idrac-" $file ; then
        model="iDRAC 6"
    elif grep -q "\-ath02" $file ; then
        model="iDRAC 6"
    elif grep -q "hnd01" $file ; then
        model="iDRAC 6"
    elif grep -q "svg01" $file ; then
        model="iDRAC 7"
    else
        model="DRAC x"
    fi
    echo $model
}

function get_model () {
    m=$( grep product $1 | head -1 | sed -e 's/product://g' )
    echo $m
}
function get_serial () {
    m=$( grep serial $1 | head -1 | sed -e 's/serial://g' )
    echo $m
}
function get_physical_proc_count () {
    C=`grep physical\ id $1 | sort | uniq | wc -l`
    echo $C
}
function get_proc_cores_count () {
    X=$( grep processor $1 | wc -l )
    echo $X
}
function get_proc_model () { 
    X=$( grep model\ name $1 | sort | uniq | sed -e 's/model name.*://g' )
    echo $X
}
function get_proc_speed () { 
    X=$( ./lshw.py all=1 section=cpu $1 | grep size | sed -e 's/size://g' )
    #X=$( grep cpu\ MHz $1 | head -1 | awk '{print $4}' )
    echo $X
}

function get_proc_bus () {
    X=$( ./lshw.py all=1 section=cpu $1 | grep clock | awk '{print $2}' )
    echo $X
}
function get_ram_total () {
    X=$( ./lshw.py all=20 section=bank $1 | grep size | awk '{print $2}' | uniq -c | tr 'GiB' ' ' | awk '{print $1*$2}' )
    echo $X
    #X=$( grep MemTotal $1 | awk '{print int($2/1024/1000)}' )
    #echo $X
}
function get_ram_dimms () {
    X=$( ./lshw.py all=20 section=bank $1 | grep size | awk '{print $2}' | uniq -c )
    echo $X | sed -e 's/ / x /g'
}
function get_ram_speed () {
    X=$( ./lshw.py all=20 section=bank $1 | grep clock | awk '{print $2}' | uniq )
    echo $X
}

function get_net_model () {
    X=$( ./lshw.py all=1 section=network $1 | grep product | sed -e 's/product://g' )
    echo $X
}
function get_net_ports () {
    x=$( grep eth[1234567890] $1 | wc -l )
    echo $x
}
function get_net_speed () {
    X=$( ./lshw.py all=1 section=network $1 | grep size | sed -e 's/size://g' |tr 'B/' 'bp' )
    echo $X
}
function get_net_driver () {
    X=$( ./lshw.py all=1 section=network $1 | grep configuration | awk '{for (i=1; i < NF; i++) { if ( $i ~ /driver=/ ) { print substr($i,length("driver=")+1,length($i)-length("driver")) ; exit} }}' )
    echo $X
}
function get_disk_total () {
    X=$( ./lshw.py all=8 section=disk $1 | grep size | awk '{if ( NF >= 3 ) { print $3} else { print $2 } }' | tr '()GB' ' ' | awk 'BEGIN{ t=0} {t+=$0} END { print t }' )
    echo $X
}
function get_disk_driver () {
    X=$( ./lshw.py all=8 section=scsi $1 | grep configuration | awk '{for (i=1; i < NF; i++) { if ( $i ~ /driver=/ ) { print substr($i,length("driver=")+1,length($i)-length("driver")) ; exit} }}' )
    if [ -z "$X" ] ; then 
        X=$( ./lshw.py all=8 section=storage $1 | grep configuration | awk '{for (i=1; i < NF; i++) { if ( $i ~ /driver=/ ) { print substr($i,length("driver=")+1,length($i)-length("driver")) ; exit} }}' )
    fi
    echo $X
}
function get_disk_count () {
    X=$( ./lshw.py all=8 section=disk $1 | grep size | wc -l )
    echo $X
}


SITE_MACHINE=site.machine
HOST_SERIAL=host.serial
HOST_MODEL=host.model
PROC_MODEL=proc.model
PROC_COUNT=proc.count
PROC_PER_CORE=proc.percore
PROC_FREQ=proc.freq
PROC_BUS=proc.bus
RAM_TOTAL=ram.total
RAM_DIMMS=ram.dimms
RAM_SPEED=ram.speed
NET_MODEL=net.model
NET_PORTS=net.ports
NET_SPEED=net.speed
NET_DRIVER=net.driver
DISK_TOTAL=disk.total
DISK_COUNT=disk.count
DISK_DRIVER=disk.driver

COLUMNS=""
COLUMNS+=$SITE_MACHINE,
COLUMNS+=$HOST_SERIAL,
COLUMNS+=$HOST_MODEL,
COLUMNS+=$PROC_MODEL,
COLUMNS+=$PROC_COUNT,
COLUMNS+=$PROC_PER_CORE,
COLUMNS+=$PROC_FREQ,
COLUMNS+=$PROC_BUS,
COLUMNS+=$RAM_TOTAL,
COLUMNS+=$RAM_DIMMS,
COLUMNS+=$RAM_SPEED,
COLUMNS+=$NET_MODEL,
COLUMNS+=$NET_PORTS,
COLUMNS+=$NET_SPEED,
COLUMNS+=$NET_DRIVER,
COLUMNS+=$DISK_TOTAL,
COLUMNS+=$DISK_COUNT,
COLUMNS+=$DISK_DRIVER
