#!/usr/bin/python

''' A ZigBee sensor network Manager
'''

import os
import sys
import serial
import select

import zigbee as ZB

# Import own stuff here...

def packetHandler():
    n = 0
    
    while True:
        packet = yield None
        n += 1
        print n, packet
        
class ZigBeeManager(object):
    def __init__(self, *args):
        self.curPacket = None
        self.coroutines = args

    def main(self, args):
        self.args = args
        self.reactor(self.args['--coordinator'])

    def reactor(self, tty, speed=9600):
        sd = serial.Serial(tty, baudrate=speed) if self.args['--testing'] is None else open(self.args['--testing'])
        self.reads = [sd, sys.stdin]
        self.writes = []
        self.handlers = dict()
        
        for cr in self.coroutines:
            packet = cr.next()
            self.handlers[packet.frame_id if packet else 0] = cr

        while True:
            errs = list(set(self.reads).union(self.writes))
            rds, wds, xds = select.select(self.reads, self.writes, errs, 5.0)

            if rds or wds or xds:
                for rd in rds: self.handleRead(rd)
                for wd in wds: self.handleWrite(wd)
                for xd in xds: self.handleError(xd)
            else:
                print 'Timeout'

    def handleRead(self, rd):
            if self.curPacket is None: self.curPacket = ZB.APIPacket()

            buf = rd.read(1)
            if len(buf) == 0: raise Exception("EOF")
            
            if self.curPacket.assemble(buf):
                if self.curPacket.goodPacket:
                    self.handlers[0].send(self.curPacket)
                else:
                    print 'Bad checksum %s vs. %s' % (hex(ord(self.curPacket.chksum())), hex(ord(self.curPacket.rawPacket[-1])))

                self.curPacket = None

    def handleWrites(self, wd):
            pass

    def handleErrors(self, wd):
            sys.exit(1)

# The test/run section

if __name__ == '__main__':

    def setbuf(fd, bufferSize):
        '''Reset an open file's I/O buffer to bufferSize - normally used to make stdout unbuffered
        '''
        fd.flush()
        return os.fdopen(fd.fileno(), fd.mode, bufferSize)

    sys.stdout = setbuf(sys.stdout, 0)
    sys.stderr = setbuf(sys.stderr, 0)

    import docopt as DO

    def main(argv):
        doc = '''%(cmd)s - Managing a ZigBee network of sensors

Usage:
  %(cmd)s [options]
  %(cmd)s -h | --help
  %(cmd)s --unittest

Options:
  -b, --speed=SPEED         The serial line speed/baud rate [default: 9600]
  -c, --coordinator=SERIAL  The tty/serial used to talk to the coordinator [default: /dev/ttyUSB0]
  -h, --help                Show this screen.
  --unittest                Run the embedded unit test suite.
  -t, --testing=TESTDATA    File with test data to read rather than serial input

Arguments:
  ARGS        Arguments
        ''' % dict(cmd=os.path.basename(sys.argv[0]))

        args = DO.docopt(doc)

        if args['--unittest']:
            sys.argv.remove('--unittest')
            return runUnitTests()

        # Your code goes here...

        return ZigBeeManager(packetHandler()).main(args)

    def runUnitTests():
        ''' Run a set of unit tests for this module
        '''
        import unittest

        class TestThis(unittest.TestCase):
            ''' Describe the TestThis test case collection
            '''
            def setUp(self):
                ''' Set up TestThis fixture
                '''
                pass

            def tearDown(self):
                ''' Tear down TestThis fixture
                '''
                pass

            def testCase_1(self):
                ''' Describe TestThis.testCase_1
                '''
                self.failUnless(False, 'Should ALWAYS fail')

            def testCase_2(self):
                ''' Describe TestThis.testCase_2
                '''
                self.failUnless(True, 'Should NEVER fail')

        class TestThat(unittest.TestCase):
            ''' Describe the TestThat test case collection
            '''
            def setUp(self):
                ''' Set up TestThat fixture
                '''
                pass

            def tearDown(self):
                ''' Tear down TestThat fixture
                '''
                pass

            def testCase_1(self):
                ''' Describe TestThat.testCase_1
                '''
                self.failUnless(False, 'Should ALWAYS fail')

            def testCase_2(self):
                ''' Describe TestThat.testCase_2
                '''
                self.failUnless(True, 'Should NEVER fail')

        suites = unittest.TestSuite()
        suites.addTest(unittest.makeSuite(TestThis))
        suites.addTest(unittest.makeSuite(TestThat))

        return unittest.TextTestRunner(verbosity=2).run(suites)

    sys.exit(main(sys.argv))
