#!/usr/bin/env bash

function err_echo () {
    echo "$@" 1>&2
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

### IMM

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

SITE_MACHINE="site.machine"
HOST_SERIAL="host.serial"
HOST_MODEL="host.model"
HOST_BIOS="host.bios"
PCU_MODEL="pcu.model"
PCU_FIRMWARE="pcu.firmware"
PCU_HARDWARE="pcu.hardware"
PCU_UPDATE="pcu.update"

LABELS=""
LABELS+="$SITE_MACHINE,"
LABELS+="$HOST_SERIAL,"
LABELS+="$HOST_MODEL,"
LABELS+="$HOST_BIOS,"
LABELS+="$PCU_MODEL,"
LABELS+="$PCU_FIRMWARE,"
LABELS+="$PCU_HARDWARE,"
LABELS+="$PCU_UPDATE"
