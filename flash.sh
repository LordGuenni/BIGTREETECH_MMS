#!/bin/bash

SCRIPTNAME="$0"
ARGS=( "$@" )

# Screen Colors
OFF='\033[0m'             # Text Reset
BLACK='\033[0;30m'        # Black
RED='\033[0;31m'          # Red
GREEN='\033[0;32m'        # Green
YELLOW='\033[0;33m'       # Yellow
BLUE='\033[0;34m'         # Blue
PURPLE='\033[0;35m'       # Purple
CYAN='\033[0;36m'         # Cyan
WHITE='\033[0;37m'        # White

B_RED='\033[1;31m'        # Bold Red
B_GREEN='\033[1;32m'      # Bold Green
B_YELLOW='\033[1;33m'     # Bold Yellow
B_CYAN='\033[1;36m'       # Bold Cyan
B_WHITE='\033[1;37m'      # Bold White

TITLE="${B_WHITE}"
DETAIL="${BLUE}"
INFO="${CYAN}"
EMPHASIZE="${B_CYAN}"
ERROR="${B_RED}"
WARNING="${B_YELLOW}"
PROMPT="${CYAN}"
DIM="${PURPLE}"
INPUT="${OFF}"
SECTION="----------------\n"

SHELL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )"/ && pwd )"

g_serial_id=""
g_fw_path=""
g_tool_path="${HOME}/katapult/scripts/flashtool.py"
g_log_en=1

log_enable() {
    g_log_en=1
}

log_disable() {
    g_log_en=0
}

log_echo() {
    if [ "${g_log_en}" -eq 0 ]; then
        return
    fi
    log_text=${1}
    echo -e "${log_text}${INPUT}"
}

prompt_123() {
    prompt=$1
    max=$2
    while true; do
        if [ -z "${max}" ]; then
            read -ep "${prompt}? " number
        elif [[ "${max}" -lt 10 ]]; then
            read -ep "${prompt} (1-${max})? " -n1 number
        else
            read -ep "${prompt} (1-${max})? " number
        fi
        if ! [[ "$number" =~ ^-?[0-9]+$ ]] ; then
            echo -e "Invalid value." >&2
            continue
        fi
        if [ "$number" -lt 1 ]; then
            echo -e "Value must be greater than 0." >&2
            continue
        fi
        if [ -n "$max" ] && [ "$number" -gt "$max" ]; then
            echo -e "Value must be less than $((max+1))." >&2
            continue
        fi
        echo ${number}
        break
    done
}

prompt_option() {
    local var_name="$1"
    local query="$2"
    shift 2
    local i=0
    for val in "$@"; do
        i=$((i+1))
        echo "$i) $val"
    done
    REPLY=$(prompt_123 "$query" "$#")
    declare -g $var_name="${!REPLY}"
}

prompt_yn() {
    while true; do
        read -n1 -p "$@ (y/n)? " yn
        case "${yn}" in
            Y|y)
                echo -n "y"
                break
                ;;
            N|n)
                echo -n "n"
                break
                ;;
            *)
                ;;
        esac
    done
}

abort(){
    if [ ! $# -eq 0 ]; then
        echo -e "${ERROR}$1${INPUT}"
    fi
    echo -e "${ERROR}Flash has been aborted!${INPUT}"
    exit -1
}

flash_vivid_mcu() {
    mapfile -t OPTIONS < <(ls /dev/serial/by-id/ | grep "vivid\|buffer" 2>/dev/null)
    local opt_num=${#OPTIONS[@]}
    if [ "${opt_num}" == 0 ]; then
        log_echo "${WARNING}${SECTION}Device serial id not found, please confirm if the ViViD cable is properly plugged in."
        abort
    else
        opt_num=${#OPTIONS[@]}

        log_echo "${PROMPT}${SECTION}Please select one of the IDs from the list below as the ID to ${PURPLE}flash${PROMPT}."
        prompt_option opt "ViViD flash serial id:" "${OPTIONS[@]}"
        if [ "${opt}" != "${NONE}" ]; then
            option_del "${opt}"
            g_serial_id=${opt}

            if [[ "$g_serial_id" == *"stm32g0b1xx"* ]]; then
                mcu="stm32g0b1xx"
            elif [[ "$g_serial_id" == *"stm32f042x6"* ]]; then
                mcu="stm32f042x6"
            else
                abort "Invalid serial id, mcu must be 'stm32g0b1xx' or 'stm32f042x6'"
            fi
            if [ -z "${g_fw_path}" ]; then
                g_fw_path="${SHELL_DIR}/firmware/klipper_${mcu}_8kb_usb.bin"
            fi

            log_echo "${PROMPT}${SECTION}ViViD flash serial id: ${PURPLE}${g_serial_id}"
            log_echo "${PROMPT}flashtool: ${PURPLE}${g_tool_path}"
            log_echo "${PROMPT}firmware: ${PURPLE}${g_fw_path}"

            python3 "${SHELL_DIR}/scripts/verify_firmware.py" ${mcu} ${g_fw_path}
            status=$?
            if [ ! $status -eq 0 ]; then
                abort "${g_fw_path}: mismatched firmware!"
            fi
            python3 "${g_tool_path}" -f "${g_fw_path}" -d "/dev/serial/by-id/${g_serial_id}"
        fi
    fi
}

verify_katapult() {
    if [ ! -e "${g_tool_path}" ]; then
        log_echo "${PURPLE}${g_tool_path}${WARNING} not installed, Please install:
${INFO}
git clone https://github.com/Arksine/katapult ${HOME}/katapult
"
        yn=$(prompt_yn "Run and install")
        echo
        if [ "$yn" = "y" ]; then
            git clone https://github.com/Arksine/katapult ${HOME}/katapult
        else
            abort "Please install ${PURPLE}katapult${ERROR}!"
        fi
    fi
}

verify_apt_package() {
    package=$1
    if ! dpkg -s "$package" >/dev/null 2>&1; then
        log_echo "${PURPLE}${package}${WARNING} not installed, Please install:
${INFO}
sudo apt install $package
"
        yn=$(prompt_yn "Run and install")
        echo
        if [ "$yn" = "y" ]; then
            sudo apt update
            if ! sudo apt install "$package"; then
                abort "${PURPLE}${package}${ERROR} installation failed!"
            fi
        else
            abort "Please install ${PURPLE}${package}${ERROR}!"
        fi
    fi
}

while getopts ":f:" opt; do
  case $opt in
    f)
      g_fw_path="$OPTARG"
      ;;
  esac
done

verify_katapult

verify_apt_package "python3-serial"

flash_vivid_mcu

# sudo apt install python3-serial
