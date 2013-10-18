#!/usr/bin/env bash

SITE_MACHINE=site_machine
HOST_SERIAL=host.serial
HOST_MODEL=host.model

##
## HOST
##
HOST_PROC_MODEL=proc.model
HOST_PROC_COUNT=proc.count
HOST_PROC_PER_CORE=proc.percore
HOST_PROC_FREQ=proc.freq
HOST_PROC_BUS=proc.bus
HOST_RAM_TOTAL=ram.total
HOST_RAM_DIMMS=ram.dimms
HOST_RAM_SPEED=ram.speed
HOST_NET_MODEL=net.model
HOST_NET_PORTS=net.ports
HOST_NET_SPEED=net.speed
HOST_NET_DRIVER=net.driver
HOST_DISK_TOTAL=disk.total
HOST_DISK_COUNT=disk.count
HOST_DISK_DRIVER=disk.driver

## 
## PCU  
##
HOST_BIOS=host.bios
PCU_MODEL=pcu.model
PCU_FIRMWARE=pcu.firmware
PCU_HARDWARE=pcu.hardware
PCU_UPDATE=pcu.update

HOST_COLUMNS=""
HOST_COLUMNS+=$SITE_MACHINE,
HOST_COLUMNS+=$HOST_SERIAL,
HOST_COLUMNS+=$HOST_MODEL,
HOST_COLUMNS+=$HOST_PROC_MODEL,
HOST_COLUMNS+=$HOST_PROC_COUNT,
HOST_COLUMNS+=$HOST_PROC_PER_CORE,
HOST_COLUMNS+=$HOST_PROC_FREQ,
HOST_COLUMNS+=$HOST_PROC_BUS,
HOST_COLUMNS+=$HOST_RAM_TOTAL,
HOST_COLUMNS+=$HOST_RAM_DIMMS,
HOST_COLUMNS+=$HOST_RAM_SPEED,
HOST_COLUMNS+=$HOST_NET_MODEL,
HOST_COLUMNS+=$HOST_NET_PORTS,
HOST_COLUMNS+=$HOST_NET_SPEED,
HOST_COLUMNS+=$HOST_NET_DRIVER,
HOST_COLUMNS+=$HOST_DISK_TOTAL,
HOST_COLUMNS+=$HOST_DISK_COUNT,
HOST_COLUMNS+=$HOST_DISK_DRIVER

PCU_COLUMNS=""
PCU_COLUMNS+=$SITE_MACHINE,
PCU_COLUMNS+=$HOST_SERIAL,
PCU_COLUMNS+=$HOST_MODEL,
PCU_COLUMNS+=$HOST_BIOS,
PCU_COLUMNS+=$PCU_MODEL,
PCU_COLUMNS+=$PCU_FIRMWARE,
PCU_COLUMNS+=$PCU_HARDWARE,
PCU_COLUMNS+=$PCU_UPDATE

function err_echo () {
    echo "$@" 1>&2
}

function sum_first_values () {
    awk 'BEGIN{sum=0} {sum+=$1} END {print sum}'
}

function format_raw_host () {
    local file=$1
    local cpufile=$2

    ./parse.py ./hostinfo/arn01/mlab3.lshw.xml "serial"
    ./parse.py ./hostinfo/arn01/mlab3.lshw.xml "product"
    ./parse.py ./hostinfo/arn01/mlab3.lshw.xml "./node/node/product/..[@class='processor']/product" | uniq
    ./parse.py ./hostinfo/arn01/mlab3.lshw.xml "./node/node/[@class='processor']"
    ./parse.py ./hostinfo/arn01/mlab3.lshw.xml "./node/node/product/..[@class='processor']/size" | uniq
    ./parse.py ./hostinfo/arn01/mlab3.lshw.xml "./node/node/product/..[@class='processor']/clock" | uniq

    ./parse.py ./hostinfo/nuq0t/mlab2.lshw.xml ".//node/..[@class='memory']/size"  # total

    ./parse.py ./hostinfo/nuq0t/mlab2.lshw.xml "./node/node/[@class='memory'][@id='memory']/size"
    ./parse.py ./hostinfo/nuq0t/mlab2.lshw.xml "./node/node/node/..[@class='memory']/size"
    ./parse.py ./hostinfo/nuq0t/mlab2.lshw.xml "./node/node/node[@class='memory']/clock" | wc -l
    ./parse.py ./hostinfo/nuq0t/mlab2.lshw.xml "./node/node/node[@class='memory'][1]/clock"

    ./parse.py ./hostinfo/nuq0t/mlab2.lshw.xml ".//node[@class='network'][1]/product"
    ./parse.py ./hostinfo/nuq0t/mlab2.lshw.xml ".//node[@class='network']/product" | wc -l
    ./parse.py ./hostinfo/nuq0t/mlab2.lshw.xml ".//node[@class='network'][1]/size"
    ./parse.py ./hostinfo/nuq0t/mlab2.lshw.xml ".//node[@class='network'][1]/configuration/setting[@id='driver']" 

    # total (one of these will work)
    ./parse.py ./hostinfo/nuq0t/mlab2.lshw.xml ".//node[@class='disk']/size" | sum_first_values
    ./parse.py ./hostinfo/nuq0t/mlab2.lshw.xml ".//node[@class='disk']/size" | wc -l
    ./parse.py ./hostinfo/nuq0t/mlab2.lshw.xml ".//node[@class='storage']/configuration/setting[@id='driver']" | uniq

    echo $HOST_SERIAL,$( get_serial $file )
    echo $HOST_MODEL,$( get_model $file )

    echo $HOST_PROC_MODEL,$( get_proc_model $cpufile ) 
    PROC_PHY_COUNT=$( get_physical_proc_count $cpufile )
    PROC_RAW_COUNT=$( get_proc_cores_count $cpufile )
    echo $HOST_PROC_COUNT,$PROC_PHY_COUNT
    echo $HOST_PROC_PER_CORE,$(( $PROC_RAW_COUNT / $PROC_PHY_COUNT ))
    echo $HOST_PROC_FREQ,$( get_proc_speed $file )
    echo $HOST_PROC_BUS,$( get_proc_bus $file )

    echo $HOST_RAM_TOTAL,$( get_ram_total $file )
    echo $HOST_RAM_DIMMS,$( get_ram_dimms $file )
    echo $HOST_RAM_SPEED,$( get_ram_speed $file )

    echo $HOST_NET_MODEL,$( get_net_model $file )
    echo $HOST_NET_PORTS,$( get_net_ports $file )
    echo $HOST_NET_SPEED,$( get_net_speed $file ) 
    echo $HOST_NET_DRIVER,$( get_net_driver $file )

    echo $HOST_DISK_TOTAL,$( get_disk_total $file )
    echo $HOST_DISK_COUNT,$( get_disk_count $file )
    echo $HOST_DISK_DRIVER,$( get_disk_driver $file )
}

function get_value_from () {
    file=$1
    label=$2
    V=`grep -E "$label" $file | sed -e 's/.*=\(.*\)$/\1/g' | tr '\n\r' ' '`
    echo $V
}
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

function get_drac_model () {
    file=$1
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


##
## IMM
##
function format_raw_imm () {
    local file=$1

    cat $file | grep -vE -- "spawn ssh|Legacy CLI|--|^\W$|Connection" | awk '
      { if (NF < 4) {next}} 
      /Type/ { prefix=$3; next; } 
      { print prefix, $0 }' | \
      awk '/Model/ { printf("'$HOST_MODEL',%s\n", $2);
                     printf("'$HOST_SERIAL',%s\n", $3); next; }
           /IMM/   { printf("'$PCU_MODEL',%s\n", $2); 
                     printf("'$PCU_FIRMWARE',%s\n", $3); 
                     printf("'$PCU_UPDATE',%s\n", $4); next; } 
           /UEFI/ { printf("'$HOST_BIOS',%s-%s\n", $3, $4); next; } 1'
    echo $PCU_HARDWARE,
}

##
## DRAC
##
function format_raw_drac () {
    local file=$1

    cat $file | \
        awk -F= '
        /Service Tag/          { printf("'$HOST_SERIAL',%s\n", $2); } 
        /System Model/         { printf("'$HOST_MODEL',%s\n", $2); }
        /System Revision/      { printf("'$HOST_MODEL',%s\n", $2); }
        /System BIOS Version/  { printf("'$HOST_BIOS',%s\n", $2); }
        /^Firmware Version/    { printf("'$PCU_FIRMWARE',%s\n", $2); }
        /^Firmware Build/      { printf("'$PCU_FIRMWARE',%s\n", $2); }
        /Last Firmware Update/ { printf("'$PCU_UPDATE',%s\n", $2); }
        /Hardware Version/     { printf("'$PCU_HARDWARE',%s\n", $2); }
        '
    echo $PCU_MODEL,$( get_drac_model $file )
}

##
## HPiLO
##
function format_raw_hpilo () {
    local file=$1

    cat $file | tr -cd '[:print:]\n' | \
        awk '/^\/system1|^\/map1/ { prefix=$1 ; next } 
             { print prefix, $1, $2, $3 }' | grep = | grep -v status | sort | \
        awk -F= '/system1 number=/      { printf("'$HOST_SERIAL',%s\n", $2); }
             /system1 name=/            { printf("'$HOST_MODEL',%s\n", $2); }
             /system1\/firmware1 version=/   { printf("'$HOST_BIOS',%s\n", $2); }
             /map1 name=/               { printf("'$PCU_MODEL',%s\n", $2); }
             /map1\/firmware1 version=/ { printf("'$PCU_FIRMWARE',%s\n", $2); }
             /map1\/firmware1 date=/    { printf("'$PCU_UPDATE',%s\n", $2); }'
    echo $PCU_HARDWARE,
}
