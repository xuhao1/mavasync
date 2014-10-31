import sys

import pymavlink.mavutil as mavutil
from pymavlink.mavutil import mavfile
from twisted.internet.protocol import *
from twisted.internet import  task
from twisted.internet import reactor

from OlviaROS.serialport import SerialPort


class mavProtocol(mavfile, Protocol):

    def __init__(self):
        device = self.transport
        self.target_system =1
        self.target_component =1
        self.l = task.LoopingCall(self.heartbeat)

        mavfile.__init__(self,0, self.transport)

    def check_link_status(self):
        #TODO:
        #  CHECK LINK
        pass


    def send_heartbeat(self):
        if self.mavlink10():
            self.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS, mavutil.mavlink.MAV_AUTOPILOT_INVALID,
                                    0, 0, 0)
        else:
            MAV_GROUND = 5
            MAV_AUTOPILOT_NONE = 4
            self.mav.heartbeat_send(MAV_GROUND, MAV_AUTOPILOT_NONE)

    def heartbeat(self):
        self.send_heartbeat()
        self.check_link_status()

    def close(self):
        print "Closing connection via {0}".format(self.host)
        self.transport.loseConnection()

    def recv(self, n=None):
        print >>sys.stderr,"This method is duplicated"

    def write(self, buf):
        try:
            self.transport.write(buf)
        except Exception as inst:
            print >>sys.stderr,"LINK via {0} down".format(self.host)

    def connectionLost(self, reason=connectionDone):
        try:
            print "LINK via {0} down by {1}".format(self.host,reason)
        except:
            print "LINK via serial port down by {0}".format(reason)

    def connect_set_up(self):
        self.linknum = 0
        pass

    def master_callback(self):
        pass
    def master_send_callback(self):
        pass

    def connectionMade(self):
        self.host = self.transport.getHost()
        print "Starting MAVLink via {0}".format(self.host)
        self.mav.set_callback(self.master_callback,self)

        if hasattr(self.mav, 'set_send_callback'):
            self.mav.set_send_callback(self.master_send_callback, self)

        self.linkerror = False
        self.link_delayed = False
        self.last_heartbeat = 0
        self.last_message = 0
        self.highest_msec = 0
        #0.1 s send heartbeat

        self.wait_heartbeat()
        self.msg_period = mavutil.periodic_event(1.0/15)
        self.connect_set_up()
        #self.WIRE_PROTOCOL_VERSION = "1.0"
        self.fd = self.transport.fileno()

        self.l.start(0.1)

    def makeConnection(self, transport):
        pass

    def dataReceived(self, data):
        self.auto_mavlink_version(data)
        msgs = self.mav.parse_buffer(data)
        if msgs:
            for msg in msgs:
                if getattr(self, '_timestamp', None) is None:
                    self.post_message(msg)
                if msg.get_type() == "BAD_DATA":
                    #print >>sys.stderr,"MAV error: %s" % msg
                    return
            print msg.__str__()
        pass

    def set_stream_rates(self):
        rate = 4
        self.mav.request_data_stream_send(self.target_system, self.targe_component,mavutil.mavlink.MAV_DATA_STREAM_ALL,
                                          rate, 1)

class Mavwithstate(mavProtocol):
    def __init__(self,mpstate):
        self.mpstate = mpstate
        mavProtocol.__init__(self)

    def connect_set_up(self):
        self.linknum =len(self.mpstate.mav_master)
        self.mpstate.mav_master.append(self)

    def set_stream_rates(self):
        '''set mavlink stream rates'''
        #TODO:
        # MAKE IT individual

        mpstate = self.mpstate
        msg_period = self.msg_period

        if (not msg_period.trigger() and
                    mpstate.status.last_streamrate1 == mpstate.settings.streamrate and
                    mpstate.status.last_streamrate2 == mpstate.settings.streamrate2):
            return
        mpstate.status.last_streamrate1 = mpstate.settings.streamrate
        mpstate.status.last_streamrate2 = mpstate.settings.streamrate2

        if self.linknum == 0:
            rate = mpstate.settings.streamrate
        else:
            rate = mpstate.settings.streamrate2
        if rate != -1:
            self.mav.request_data_stream_send(mpstate.status.target_system, mpstate.status.target_component,
                                              mavutil.mavlink.MAV_DATA_STREAM_ALL,
                                              rate, 1)


def testReadSerial():
    SerialPort(mavProtocol(), '/dev/tty.usbmodem14131', reactor, baudrate=115200)
    reactor.run()

if __name__=="__main__":
    testReadSerial()
