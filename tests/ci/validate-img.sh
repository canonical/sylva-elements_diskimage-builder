#!/bin/bash

if [ ${DIB_DEBUG_TRACE:-0} -gt 0 ]; then
	set -x
fi
set -eu

# Default parameters
VM_SSH_PORT=${VM_SSH_PORT:-8888}
VM_SERIAL_FILE=${VM_SERIAL_FILE:-/tmp/serial.log}
VM_STR_SEARCH=${VM_STR_SEARCH:-"login:"}
VM_BOOT_MODE=${VM_BOOT_MODE:-uefi}
MONITOR_WAIT=${MONITOR_WAIT:-10}
MONITOR_NB_RETRY=${MONITOR_NB_RETRY:-120}

# Local vars
RET_CODE=1
VM_OPTIONS=""
VM_DEFAULT_OPTIONS="-machine q35,smm=on -m 2G -no-user-config -nic user,hostfwd=tcp::${VM_SSH_PORT}-:22 -hda ${1} -vnc :0 -vga virtio -chardev stdio,id=char0,logfile=${VM_SERIAL_FILE},signal=off -serial chardev:char0"
OVMF_UEFI_CODE="/usr/share/OVMF/OVMF_CODE_4M.fd"
OVMF_UEFI_VARS="/usr/share/OVMF/OVMF_VARS_4M.fd"
OVMF_SB_CODE="/usr/share/OVMF/OVMF_CODE_4M.ms.fd"
OVMF_SB_VARS="/usr/share/OVMF/OVMF_VARS_4M.ms.fd"

# Determine which boot mode using
case `echo ${VM_BOOT_MODE} | tr '[:upper:]' '[:lower:]'` in

	legacy)
		VM_OPTIONS="-smp 2"
		;;

	uefi)
		VM_OPTIONS="-smp 2 -global driver=cfi.pflash01,property=secure,value=on -drive if=pflash,format=raw,unit=0,file=${OVMF_UEFI_CODE},readonly=on -drive if=pflash,format=raw,unit=1,file=${OVMF_UEFI_VARS}"
		;;

	secureboot)
		VM_OPTIONS="-smp 1 -cpu qemu64-v1 -boot strict=on -global driver=cfi.pflash01,property=secure,value=on -drive if=pflash,format=raw,unit=0,file=${OVMF_SB_CODE},readonly=on -drive if=pflash,format=raw,unit=1,file=${OVMF_SB_VARS}"
		;;

	*)
		echo "Unknown boot mode"
		exit 10
		;;

esac

# Reset output file
rm -f ${VM_SERIAL_FILE}
echo "" > ${VM_SERIAL_FILE}

# Start VM
(qemu-system-x86_64 ${VM_DEFAULT_OPTIONS} ${VM_OPTIONS} 2>&1 | tee -a $VM_SERIAL_FILE) &

until [ $MONITOR_NB_RETRY -lt 1 ]; do
	# Check output log
	if grep -q "${VM_STR_SEARCH}" ${VM_SERIAL_FILE}; then
		# Found the string, VM booted so we exit without error
		RET_CODE=0
		break
	fi
	# Nothing found and counter is still valid
	MONITOR_NB_RETRY=$((MONITOR_NB_RETRY-1))
	sleep ${MONITOR_WAIT}
done

# Kill the qemu process
pkill -f "qemu-system-x86_64"

exit ${RET_CODE}
