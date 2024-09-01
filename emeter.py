#!/usr/bin/env python3

"""
SMA Emeter

SMA Emeter
"""

##------------------------------------------------------------
_AUTHOR    = 'RP'
_VERSION   = '0.1.0'
_COPYRIGHT = '(c) 2024'

_ABOUT = _AUTHOR + '  v' + _VERSION + '   ' + _COPYRIGHT
##------------------------------------------------------------

import socket
import ipaddress
import struct
import time

# Constants

# Big endian format
# typedef struct
# {  HEADER
#    unsigned char idString[4];         off      0
#    unsigned char _4[2];               off      4
#    unsigned char tag[2];              off      6
#    unsigned char group[4];            off      8
#    unsigned char length[2];           off     12
#    unsigned char smaNet2[2];          off     14
#    unsigned char protID[2];           off     16
#    unsigned char susy[2];             off     18
#    unsigned char serno[4];            off     20
#    unsigned char ticker[4];           off     24
#    CHANNELS
#    unsigned char channels[1500];      off     28
# } EMETER_DATA2;

_MC_IP_ADDR = "239.12.255.254"
_PORT = 9522

_EMETER_HEADER_FORMAT = ">4sHHIHHHHII"
_EMETER_HEADER_SIZE = struct.calcsize(_EMETER_HEADER_FORMAT)   # Size 28

_VALSIZE4 = ">I"
_VALSIZE8 = ">Q"
_OBISTAG  = ">4B"

# OBIS_TAG indices
_CHNIDX    = 0
_VALIDX    = 1
_TYPEIDX   = 2
_TARIFFIDX = 3

# Value list indice, including OBIS_TAG indices 0 .. 3
_VALUEIDX = 4

# Measurement types
_TYPE4 = 4
_TYPE8 = 8

# Measurement indices
_ALL_ACT_POWER_FROM_GRID  = 1
_ALL_ACT_POWER_TO_GRID    = 2
_PHASE1_ACT_PWR_FROM_GRID = 21
_PHASE1_ACT_PWR_TO_GRID   = 22
_PHASE1_CURRENT           = 31
_PHASE1_VOLTAGE           = 32
_PHASE2_ACT_PWR_FROM_GRID = 41
_PHASE2_ACT_PWR_TO_GRID   = 42
_PHASE2_CURRENT           = 51
_PHASE2_VOLTAGE           = 52
_PHASE3_ACT_PWR_FROM_GRID = 61
_PHASE3_ACT_PWR_TO_GRID   = 62
_PHASE3_CURRENT           = 71
_PHASE3_VOLTAGE           = 72

# The resolution of individual physical values
# 0.1 W
# 1 Ws
# 1 mA
# 1 mV
# 0.001 for cos(φ)

class UDPReceiver(object):
    def __init__(self, ip_addr, port, bufsize):
        self.bufsize = bufsize

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((ip_addr, port))

        if ipaddress.IPv4Address(ip_addr).is_multicast:
            mreq = struct.pack("4sl", socket.inet_aton(ip_addr), socket.INADDR_ANY)
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        print("Receiving on %s:%d\n" % (ip_addr, port))

    def __del__(self):
        self.sock.close()

    def receive(self):
        return self.sock.recvfrom(self.bufsize)


def find_all_tags(chn_list, emdat, offset):
    chn_list.clear()

    while offset < len(emdat):
        dat = list(struct.unpack_from(_OBISTAG, emdat, offset))

        #print(dat)

        if dat[_TYPEIDX] == _TYPE8:
            valsize = _VALSIZE8
        elif dat[_TYPEIDX] == _TYPE4:
            valsize = _VALSIZE4
        else:
            break

        val = struct.unpack_from(valsize, emdat, offset+struct.calcsize(_OBISTAG))
        #print(val)
        dat.append(val[0])
        #print(dat)
        chn_list.append(dat)

        offset += struct.calcsize(_OBISTAG) + dat[_TYPEIDX]

    return offset


def filter_out(chn_list, typ, idx):
    val = [v[_VALUEIDX] for v in chn_list if v[_TYPEIDX] == typ and v[_VALIDX] == idx]
    return val[0]

def handle_value_units(val, idx):
    if idx == _ALL_ACT_POWER_FROM_GRID  or \
       idx == _ALL_ACT_POWER_TO_GRID    or \
       idx == _PHASE1_ACT_PWR_FROM_GRID or \
       idx == _PHASE1_ACT_PWR_TO_GRID   or \
       idx == _PHASE2_ACT_PWR_FROM_GRID or \
       idx == _PHASE2_ACT_PWR_TO_GRID   or \
       idx == _PHASE3_ACT_PWR_FROM_GRID or \
       idx == _PHASE3_ACT_PWR_TO_GRID:
        return ("W", val // 10)
    elif idx == _PHASE1_CURRENT or \
         idx == _PHASE2_CURRENT or \
         idx == _PHASE3_CURRENT:
        return ("A", val // 1000)
    elif idx == _PHASE1_VOLTAGE or \
         idx == _PHASE2_VOLTAGE or \
         idx == _PHASE3_VOLTAGE:
        return ("V", val // 1000)

    return -1, ""


def handle_chn_act_values_units(chn_list, idx):
    val = filter_out(chn_list, _TYPE4, idx)
    return handle_value_units(val, idx)


if __name__ == '__main__':
    from optparse import OptionParser

    op = OptionParser(version = '%prog   ' + _ABOUT)

    op.add_option("-a", "--mcipaddr",  dest="mcipaddr", type="string", help="MC IP address", default=_MC_IP_ADDR)
    op.add_option("-p", "--port",  dest="port", type="int", help="Port", default=_PORT)

    (options, args) = op.parse_args()

    #print(options)
    #print(args)

    # Invalid arguments are given
    if len(args) > 0:
        print(_ABOUT)
        op.print_help()
        op.exit()

    print("MC IP address: %s" % options.mcipaddr)
    print("Port: %d\n" % options.port)

    udp_recv = UDPReceiver(options.mcipaddr, options.port, 1024)

    while True:
        data, addr = udp_recv.receive()

        print(f"Receive message from {addr} with length {len(data)}")
        print(_EMETER_HEADER_SIZE)

        s = struct.unpack_from(_EMETER_HEADER_FORMAT, data)

        print(s)
        print("ID      %s"   % s[0])
        print("4       %04X" % s[1])
        print("TAG     %04X" % s[2])
        print("GROUP   %08X" % s[3])
        print("LENGTH  %d"   % s[4])
        print("SMANET2 %04X" % s[5])
        print("PROTID  %04X" % s[6])
        print("SUSY    %d"   % s[7])
        print("SERNO   %d"   % s[8])
        print("SN      %05d%010d" % (s[7], s[8]))
        print("TICKER  %d" % s[9])

        cl = []    # [[CHNIDX, VALIDX, TYPEIDX, TARIFFIDX, VALUE], ...]
        ans = find_all_tags(cl, data, _EMETER_HEADER_SIZE)
        #print(ans)
        #print(cl)

        print("-----------------------------")
        print("---From Grid SUM [%s]: %d" % handle_chn_act_values_units(cl, _ALL_ACT_POWER_FROM_GRID))
        print("---From Grid P1  [%s]: %d" % handle_chn_act_values_units(cl, _PHASE1_ACT_PWR_FROM_GRID))
        print("---From Grid P2  [%s]: %d" % handle_chn_act_values_units(cl, _PHASE2_ACT_PWR_FROM_GRID))
        print("---From Grid P3  [%s]: %d" % handle_chn_act_values_units(cl, _PHASE2_ACT_PWR_FROM_GRID))
        print("---To Grid SUM   [%s]: %d" % handle_chn_act_values_units(cl, _ALL_ACT_POWER_TO_GRID))
        print("---To Grid P1    [%s]: %d" % handle_chn_act_values_units(cl, _PHASE1_ACT_PWR_TO_GRID))
        print("---To Grid P2    [%s]: %d" % handle_chn_act_values_units(cl, _PHASE2_ACT_PWR_TO_GRID))
        print("---To Grid P3    [%s]: %d" % handle_chn_act_values_units(cl, _PHASE2_ACT_PWR_TO_GRID))

        print("-----------------------------")
        print("---Voltage P1    [%s]: %d" % handle_chn_act_values_units(cl, _PHASE1_VOLTAGE))
        print("---Current P1    [%s]: %d" % handle_chn_act_values_units(cl, _PHASE1_CURRENT))
        print("---Voltage P2    [%s]: %d" % handle_chn_act_values_units(cl, _PHASE2_VOLTAGE))
        print("---Current P2    [%s]: %d" % handle_chn_act_values_units(cl, _PHASE2_CURRENT))
        print("---Voltage P3    [%s]: %d" % handle_chn_act_values_units(cl, _PHASE3_VOLTAGE))
        print("---Current P3    [%s]: %d" % handle_chn_act_values_units(cl, _PHASE3_CURRENT))

        print("-----------------------------")
        print("%s" % time.ctime())
        print("-----------------------------------------------------------------")



