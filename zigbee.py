#!/usr/bin/python

''' Describe the content of this file
'''

import os
import sys
from struct import *
import hd

# Import own stuff here...

class UniqueFrameID():
    def __init__(self):
        self.id = 0
        
    def __call__(self):
        self.id = (self.id + 1)&0xff
        if self.id == 0: self.id = 1
        return pack('>B', self.id)

uniqueFrameIDs = UniqueFrameID()

FrameTypes = dict(AT='\x08', ATQueue='\x09', ZBTransmit='\x10', ZBCommandFrame='\x11', RemoteAT='\x17',
                  CreateSourceRoute='\x21', ATResponse='\x88', ModemStatus='\x8a', ZBTransmitStatus='\x8b',
                  ZBReceivePacket='\x90', ZBRxIndicator='\x91', ZBIOSample='\x92', XBeeSensorRead='\x94',
                  NodeIdentification='\x95', RemoteCommandResponse='\x97', FirmwareUpdateStatus='\xa0', 
                  RouteRecordIndicator='\xa1', RouteRequestIndicator='\xa3', )

def string(arg, width):
     if isinstance(arg, int):
         fmt = ('>B' if arg <= 0xff else '>H' if arg <= 0xffff else '>I') if width == 0 else '>%c' % ('BBHII'[width])
         arg = pack(fmt, arg)
     
     return arg

class APIPacket(dict):
    ''' Describe class
    '''
    EMPTY, LENGTH, BODY, CHKSUM, COMPLETE = range(1,6)    # Assembly states
    FRAME, ESCAPE, XON, XOFF = escapeBytes = ('\x7e', '\x7d', '\x11', '\x13')   # Special bytes
    BROADCAST = '\x00'*6 + '\xff'*2
    UNKNOWN = '\xff\xfe'
    COORDINATOR = '\x00'*8

    def __init__(self, content='', escaped=True, assemblyState=EMPTY, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.rawPacket, self.escaped, self.assemblyState = content, escaped, assemblyState
        self.lastWasEscape = False
        self.length = unpack('>H', content[1:3]) if content else 0
        self.goodPacket = (self.assemblyState == self.COMPLETE and self.goodChkSum()) if content else False
         
    def append(self, c):
        if self.escaped:
            if self.lastWasEscape:
                # print 'escape', hex(ord(c))
                c = chr(ord(c)^0x20)
                self.lastWasEscape = False
            else:
                self.lastWasEscape = c == self.ESCAPE

        if not self.lastWasEscape:
            self.rawPacket += c

        return len(self.rawPacket)

    def chksum(self, frame=None):
        if frame is None: frame = self.rawPacket[3:-1]
        return chr(0xff - (sum([ord(x) for x in frame])&0xff))
    
    def goodChkSum(self):
        return ord(self.chksum(self.rawPacket[3:])) == 0

    def assemble(self, buf):
        for c in buf:
            if self.assemblyState == self.EMPTY:
                if c == self.FRAME:
                    self.append(c)
                    self.assemblyState = self.LENGTH
                else:
                    print 'dropping', hex(ord(c))
            elif self.assemblyState == self.LENGTH:
                if self.append(c) == 3:
                    self.length = unpack('>H', self.rawPacket[1:])[0]
                    self.assemblyState = self.BODY
            elif self.assemblyState == self.BODY:
                if self.append(c) == self.length + 3:
                    self.assemblyState = self.CHKSUM
            elif self.assemblyState == self.CHKSUM:
                if self.append(c) == self.length + 4:
                    self.goodPacket = self.goodChkSum()
                    self.assemblyState = self.COMPLETE

        return self.assemblyState == self.COMPLETE

    def build(self, frameType, frameID=None):
        if frameID is None: frameID = uniqueFrameIDs()
        frame = frameType + frameID + self.frameData()
        self.length = len(frame)
        length = string(self.length, 2)
        self.rawPacket = self.FRAME + length + frame + self.chksum(frame)
        if self.escaped: self.rawPacket = self.FRAME + self.escape(self.rawPacket[1:])
        self.assemblyState = self.COMPLETE
        self.goodPacket = True
        
    def escape(self, buffer):
        result = ''
        
        for c in buffer:
            if c in self.escapeBytes: 
                result += self.ESCAPE
                c = chr(ord(c)^0x20)
                
            result += c
            
        return result
        
    def __repr__(self):
        return hd.hd(self.rawPacket)

class AT(APIPacket):
    def __init__(self, *args, **kwargs):
        APIPacket.__init__(self, escaped=kwargs.get('escaped', True))
        self.args, self.kwargs = args, kwargs
        self.build(FrameTypes['AT'], kwargs.get('frameID'))
        
    def frameData(self):
        fd = self.args[0]
        if len(self.args) == 2: fd += string(self.args[1], 0) 
        return fd
    
    def disAssemble(self):
        fmt = '>BHBB2s%dsB' % (len(self.rawPacket) - self.length - 3)
        d = dict(zip(('start', 'length', 'frameType', 'frameID', 'command', 'parameter', 'checksum'), unpack(fmt, self.rawPacket)))
        self.update(d)
        return dict(self)

class ATQueue(APIPacket):
    def __init__(self, *args, **kwargs):
        APIPacket.__init__(self, escaped=kwargs.get('escaped', True))
        self.args, self.kwargs = args, kwargs
        self.build(FrameTypes['ATQueue'], kwargs.get('frameID'))
        
    def frameData(self):
        fd = self.args[0]
        if len(self.args) == 2: fd += string(self.args[1], 0) 
        return fd
               
class RemoteAT(APIPacket):
    def __init__(self, *args, **kwargs):
        APIPacket.__init__(self, escaped=kwargs.get('escaped', True))
        self.args, self.kwargs = args, kwargs
        self.build(FrameTypes['RemoteAT'], kwargs.get('frameID'))
        
    def frameData(self):
        fd = self.kwargs.get('dest', self.BROADCAST)
        fd += self.kwargs.get('network', self.UNKNOWN)
        fd += string(self.kwargs.get('options', 2), 1)
        fd += self.args[0]
        if len(self.args) == 2: fd += string(self.args[1], 0)
        return fd
        
class ZBTransmitExplicit(APIPacket):
    def __init__(self, *args, **kwargs):
        APIPacket.__init__(self, escaped=kwargs.get('escaped', True))
        self.args, self.kwargs = args, kwargs
        self.build(FrameTypes['ZBTransmitExplicit'], kwargs.get('frameID'))
        
    def frameData(self):
        fd = self.kwargs.get('dest', self.BROADCAST)
        fd += self.kwargs.get('network', self.UNKNOWN)
        fd += string(self.kwargs.get('source', 0), 1)
        fd += string(self.kwargs.get('destination', 0), 1)
        fd += string(self.kwargs.get('cluster', 0), 2)
        fd += string(self.kwargs.get('profile', 0), 2)
        fd += string(self.kwargs.get('radius', 0), 1)
        fd += string(self.kwargs.get('options', 0), 1)
        fd += self.args[0]

class ZBTransmit(APIPacket):
    def __init__(self, *args, **kwargs):
        APIPacket.__init__(self, escaped=kwargs.get('escaped', True))
        self.args, self.kwargs = args, kwargs
        self.build(FrameTypes['ZBTransmit'], kwargs.get('frameID'))
        
    def frameData(self):
        fd = self.kwargs.get('dest', self.BROADCAST)
        fd += self.kwargs.get('network', self.UNKNOWN)
        fd += string(self.kwargs.get('radius', 0), 1)
        fd += string(self.kwargs.get('options', 0), 1)
        fd += self.args[0]

        return fd
        
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
        doc = '''%(cmd)s - Short description

Optional longer description

Usage:
  %(cmd)s [options] [ARGS]...
  %(cmd)s -h | --help
  %(cmd)s --unittest

Options:
  -h, --help  Show this screen.
  --unittest  Run the embedded unit test suite.

Arguments:
  ARGS        Arguments
        ''' % dict(cmd=os.path.basename(sys.argv[0]))

        args = DO.docopt(doc)

        if args['--unittest']:
            sys.argv.remove('--unittest')
            return runUnitTests()

        # Your code goes here...

        return 0

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
                ''' PacketBuild
                '''
                print AT('ND')
                at = AT('WR', 10)
                print at
                print at.disAssemble()
                open('/tmp/xbee.data', 'a').write(at.rawPacket)
                print ATQueue('SM', 0)
                print RemoteAT('IR', 1000)
                print ZBTransmit('TxData1B')

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
        #suites.addTest(unittest.makeSuite(TestThat))

        return unittest.TextTestRunner(verbosity=2).run(suites)

    sys.exit(main(sys.argv))
