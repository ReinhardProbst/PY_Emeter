#!/usr/bin/env python3

"""
SMA EMeter

SMA EMeter
"""

##------------------------------------------------------------
_AUTHOR    = 'RP'
_VERSION   = '0.5.0'
_COPYRIGHT = '(c) 2024'

_ABOUT = _AUTHOR + '  v' + _VERSION + '   ' + _COPYRIGHT
##------------------------------------------------------------

import socket
import ipaddress
import struct
import time


# Constants

MC_IP_ADDR = "239.12.255.254"
PORT = 9522


class UDPReceiver(object):
    """
    UDPReceiver

    UDPReceiver
    """
    def __init__(self, ip_addr, port, bufsize, diag = False):
        self.bufsize = bufsize

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((ip_addr, port))

        if ipaddress.IPv4Address(ip_addr).is_multicast:
            mreq = struct.pack("4sl", socket.inet_aton(ip_addr), socket.INADDR_ANY)
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        if diag:
            print("Receiving on %s:%d\n" % (ip_addr, port))

    def __del__(self):
        self.sock.close()

    def receive(self):
        return self.sock.recvfrom(self.bufsize)


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


class EMeter(object):
    """
    EMeter

    Emeter
    """

    EMETER_HEADER_FORMAT = ">4sHHIHHHHII"
    EMETER_HEADER_SIZE = struct.calcsize(EMETER_HEADER_FORMAT)   # Size 28

    VAL4 = ">I"
    VAL8 = ">Q"
    OBISTAG  = ">4B"

    # OBIS_TAG indices
    CHNIDX    = 0
    VALIDX    = 1
    TYPEIDX   = 2
    TARIFFIDX = 3

    # Value list indix, including OBIS_TAG indices 0 .. 3
    VALUEIDX = 4

    # Measurement types
    TYPE4 = 4
    TYPE8 = 8

    # Measurement values indices
    ALL_ACT_POWER_FROM_GRID  = 1
    ALL_ACT_POWER_TO_GRID    = 2
    PHASE1_ACT_PWR_FROM_GRID = 21
    PHASE1_ACT_PWR_TO_GRID   = 22
    PHASE1_CURRENT           = 31
    PHASE1_VOLTAGE           = 32
    PHASE2_ACT_PWR_FROM_GRID = 41
    PHASE2_ACT_PWR_TO_GRID   = 42
    PHASE2_CURRENT           = 51
    PHASE2_VOLTAGE           = 52
    PHASE3_ACT_PWR_FROM_GRID = 61
    PHASE3_ACT_PWR_TO_GRID   = 62
    PHASE3_CURRENT           = 71
    PHASE3_VOLTAGE           = 72

    # The resolution of individual physical values
    # 0.1 W
    # 1 Ws
    # 1 mA
    # 1 mV
    # 0.001 for cos(φ)

    def __init__(self, diag = False):
        self.cl = []    # [[CHNIDX, VALIDX, TYPEIDX, TARIFFIDX, VALUE], ...]
        self.header = {}
        self.js = {}
        self.emdat = None
        self.diag = diag

    def update(self, emdat):
        self.emdat = emdat

    def get_header(self):
        self.header.clear()

        h = struct.unpack_from(EMeter.EMETER_HEADER_FORMAT, self.emdat)

        if self.diag:
            print(h)

        self.header["ID"]      = str(h[0])
        self.header["4"]       = "{:04X}".format(h[1])
        self.header["TAG"]     = "{:04X}".format(h[2])
        self.header["GROUP"]   = "{:08X}".format(h[3])
        self.header["LENGTH"]  = h[4] # "{:d}".format(h[4])
        self.header["SMANET2"] = "{:04X}".format(h[5])
        self.header["PROTID"]  = "{:04X}".format(h[6])
        self.header["SUSY"]    = "{:d}".format(h[7])
        self.header["SERNO"]   = "{:d}".format(h[8])
        self.header["TICKER"]  = h[9] # "{:d}".format(h[9])

        return self.header

    def extract_all_channels(self):
        self.cl.clear()

        offset = EMeter.EMETER_HEADER_SIZE

        while offset < len(self.emdat):
            dat = list(struct.unpack_from(EMeter.OBISTAG, self.emdat, offset))

            if dat[EMeter.TYPEIDX] == EMeter.TYPE8:
                valsize = EMeter.VAL8
            elif dat[EMeter.TYPEIDX] == EMeter.TYPE4:
                valsize = EMeter.VAL4
            else:
                if self.diag:
                    print("Unexpected type %d/%d/%d/%d" % (dat[EMeter.CHNIDX], dat[EMeter.VALIDX], dat[EMeter.TYPEIDX], dat[EMeter.TARIFFIDX]))
                break

            val = struct.unpack_from(valsize, self.emdat, offset+struct.calcsize(EMeter.OBISTAG))
            dat.append(val[0])

            if self.diag:
                print(dat)  

            self.cl.append(dat)

            offset += struct.calcsize(EMeter.OBISTAG) + dat[EMeter.TYPEIDX]

        return None

    def helper_extract_act_values(self, idx):
        return [v[EMeter.VALUEIDX] for v in self.cl if v[EMeter.TYPEIDX] == EMeter.TYPE4 and v[EMeter.VALIDX] == idx][0]

    def get_act_pwr_all_from_grid(self):
        return ("W", self.helper_extract_act_values(EMeter.ALL_ACT_POWER_FROM_GRID) // 10)

    def get_act_pwr_all_to_grid(self):
        return ("W", self.helper_extract_act_values(EMeter.ALL_ACT_POWER_TO_GRID) // 10)

    def get_act_pwr_phase1_from_grid(self):
        return ("W", self.helper_extract_act_values(EMeter.PHASE1_ACT_PWR_FROM_GRID) // 10)
    
    def get_act_pwr_phase1_to_grid(self):
        return ("W", self.helper_extract_act_values(EMeter.PHASE1_ACT_PWR_TO_GRID) // 10)
    
    def get_act_pwr_phase2_from_grid(self):
        return ("W", self.helper_extract_act_values(EMeter.PHASE2_ACT_PWR_FROM_GRID) // 10)
    
    def get_act_pwr_phase2_to_grid(self):
        return ("W", self.helper_extract_act_values(EMeter.PHASE2_ACT_PWR_TO_GRID) // 10)
    
    def get_act_pwr_phase3_from_grid(self):
        return ("W", self.helper_extract_act_values(EMeter.PHASE3_ACT_PWR_FROM_GRID) // 10)
    
    def get_act_pwr_phase3_to_grid(self):
        return ("W", self.helper_extract_act_values(EMeter.PHASE3_ACT_PWR_TO_GRID) // 10)
    
    def get_act_pwr_phase1_current(self):
        return ("A", self.helper_extract_act_values(EMeter.PHASE1_CURRENT) // 1000)
    
    def get_act_pwr_phase1_voltage(self):    
        return ("V", self.helper_extract_act_values(EMeter.PHASE1_VOLTAGE) // 1000)
    
    def get_act_pwr_phase2_current(self):
        return ("A", self.helper_extract_act_values(EMeter.PHASE2_CURRENT) // 1000)
    
    def get_act_pwr_phase2_voltage(self):    
        return ("V", self.helper_extract_act_values(EMeter.PHASE2_VOLTAGE) // 1000)
    
    def get_act_pwr_phase3_current(self):
        return ("A", self.helper_extract_act_values(EMeter.PHASE3_CURRENT) // 1000)
    
    def get_act_pwr_phase3_voltage(self):    
        return ("V", self.helper_extract_act_values(EMeter.PHASE3_VOLTAGE) // 1000)
    
    def get_javascript(self):
        self.js.clear()

        self.js = self.get_header() 
        self.extract_all_channels()

        chn = {"chn1": ("dW", self.helper_extract_act_values(EMeter.ALL_ACT_POWER_FROM_GRID) ), # dW == 0.1 W (deciWatt)
               "chn21":("dW", self.helper_extract_act_values(EMeter.PHASE1_ACT_PWR_FROM_GRID)),
               "chn41":("dW", self.helper_extract_act_values(EMeter.PHASE2_ACT_PWR_FROM_GRID)),
               "chn61":("dW", self.helper_extract_act_values(EMeter.PHASE3_ACT_PWR_FROM_GRID)),
               "chn2": ("dW", self.helper_extract_act_values(EMeter.ALL_ACT_POWER_TO_GRID)   ),     
               "chn22":("dW", self.helper_extract_act_values(EMeter.PHASE1_ACT_PWR_TO_GRID)  ),
               "chn42":("dW", self.helper_extract_act_values(EMeter.PHASE2_ACT_PWR_TO_GRID)  ),
               "chn62":("dW", self.helper_extract_act_values(EMeter.PHASE3_ACT_PWR_TO_GRID)  )}

        self.js.update(chn)
        
        return self.js
    

if __name__ == '__main__':
    """
    MAIN

    Demonstrate usage of UDPReceiver and EMeter classes
    """
        
    from optparse import OptionParser

    op = OptionParser(version = '%prog   ' + _ABOUT)

    op.add_option("-a", "--mcipaddr",  dest="mcipaddr", type="string", help="MC IP address", default=MC_IP_ADDR)
    op.add_option("-p", "--port",  dest="port", type="int", help="Port", default=PORT)
    op.add_option("-j", "--js",  dest="js", action="store_true", help="JavaScript", default=False)

    (options, args) = op.parse_args()

    if not options.js:
        print(options)
        print(args)

    # Invalid arguments are given
    if len(args) > 0:
        print(_ABOUT)
        op.print_help()
        op.exit()

    if not options.js:
        print("MC IP address: %s" % options.mcipaddr)
        print("Port: %d\n" % options.port)

    udp_recv = UDPReceiver(options.mcipaddr, options.port, 1024, not options.js)

    em = EMeter(not options.js)

    while True:
        data, addr = udp_recv.receive()

        if not options.js:
            print(f"Receive message from {addr} with length {len(data)}")

        em.update(data)

        h = em.get_header()
        if not options.js:
            print("---HEADER:")
            print(h)

        em.extract_all_channels()

        if not options.js: 
            print("---MEASUREMENT VALUES:")
            print("From Grid ALL [%s]: %d" % em.get_act_pwr_all_from_grid())
            print("From Grid P1  [%s]: %d" % em.get_act_pwr_phase1_from_grid())
            print("From Grid P2  [%s]: %d" % em.get_act_pwr_phase2_from_grid())
            print("From Grid P3  [%s]: %d" % em.get_act_pwr_phase3_from_grid())
            print("---------------------------------------")
            print("To Grid ALL   [%s]: %d" % em.get_act_pwr_all_to_grid())
            print("To Grid P1    [%s]: %d" % em.get_act_pwr_phase1_to_grid())
            print("To Grid P2    [%s]: %d" % em.get_act_pwr_phase2_to_grid())
            print("To Grid P3    [%s]: %d" % em.get_act_pwr_phase3_to_grid())
            print("---------------------------------------")
            print("Voltage P1    [%s]: %d" % em.get_act_pwr_phase1_voltage())
            print("Current P1    [%s]: %d" % em.get_act_pwr_phase1_current())
            print("Voltage P2    [%s]: %d" % em.get_act_pwr_phase2_voltage())
            print("Current P2    [%s]: %d" % em.get_act_pwr_phase2_current())
            print("Voltage P3    [%s]: %d" % em.get_act_pwr_phase3_voltage())
            print("Current P3    [%s]: %d" % em.get_act_pwr_phase3_current())
            print("%s" % time.ctime())
            print("------------------------------------------------------------------------------")
        else:
            js = em.get_javascript()
            #print(js)
            UNIT = 0
            VALUE = 1
            delta_from_to = js["chn1"][VALUE] - js["chn2"][VALUE]
            p123_from_grid = js["chn21"][VALUE] + js["chn41"][VALUE] + js["chn61"][VALUE]
            p123_to_grid  = js["chn22"][VALUE] + js["chn42"][VALUE] + js["chn62"][VALUE]
            print("From Grid ALL       [%s]: %d" % (js["chn1" ][UNIT], js["chn1" ][VALUE]))
            print("To Grid ALL         [%s]: %d" % (js["chn2" ][UNIT], js["chn2" ][VALUE]))
            print("---------------------------------------")
            print("From Grid P1        [%s]: %d" % (js["chn21"][UNIT], js["chn21"][VALUE]))
            print("From Grid P2        [%s]: %d" % (js["chn41"][UNIT], js["chn41"][VALUE]))
            print("From Grid P3        [%s]: %d" % (js["chn61"][UNIT], js["chn61"][VALUE]))
            print("From Grid P1+P2+P3  [%s]: %d" % (js["chn21"][UNIT], p123_from_grid))            
            print("---------------------------------------")
            print("To Grid P1          [%s]: %d" % (js["chn22"][UNIT], js["chn22"][VALUE]))
            print("To Grid P2          [%s]: %d" % (js["chn42"][UNIT], js["chn42"][VALUE]))
            print("To Grid P3          [%s]: %d" % (js["chn62"][UNIT], js["chn62"][VALUE]))
            print("To Grid P1+P2+P3    [%s]: %d" % (js["chn22"][UNIT], p123_to_grid))
            print("---------------------------------------")
            print("Delta Grid from/to  [%s]: %d" % (js["chn1"][UNIT], delta_from_to))
            print("Delta Grid P1+P2+P3 [%s]: %d" % (js["chn22"][UNIT], p123_from_grid - p123_to_grid))
            print("------------------------------------------------------------------------------")


