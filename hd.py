#!/usr/bin/python

''' HexDump a buffer
'''

import os
import sys

# Import own stuff here...

def hd(buf, N=16, header=None):
    lines = []
    if N > 16: N = 16
    lenHeader = 5

    if header is not None:
        lenHeader = len(header) + 1
        if lenHeader < 5: lenHeader = 5
        lines.append('%*s' % (1 - lenHeader, header) + ' | ' + ' '.join(['%02x'%x for x in xrange(N)]) + ' | ' +
             ''.join(['%x'%x for x in xrange(N)]) + ' |')
        lines.append('|'.join(['-'*lenHeader, '-'*(3*N + 1), '-'*(N + 2), '']))

    pos = 0

    while True:
        segment = buf[pos:pos + N]

        if segment:
            n = N - len(segment)
            hex = ' '.join(['%02x' % (ord(x)) for x in segment]) + ' ..'*n
            ascii = ''.join([x if 32 <= ord(x) < 127 else '.' for x in segment]) + ' '*n
            lines.append('%s%04x | %s | %s |' % (' '*(lenHeader - 5), pos, hex, ascii))
            pos += N
        else:
            break

    if header:
        lines.append(lines[1])
        lines.append(lines[0])

    return '\n'.join(lines)

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
  %(cmd)s [options] [FILE]...
  %(cmd)s -h | --help
  %(cmd)s --unittest

Options:
  -n, --columns=N  Number of columns, max 16 [default: 16]
  --header=HEADER  Emit header and trailer with HEADER in top left corner
  -h, --help       Show this screen.
  --unittest       Run the embedded unit test suite.

Arguments:
  FILE        File to HexDump. Default is STDIN
        ''' % dict(cmd=os.path.basename(sys.argv[0]))

        args = DO.docopt(doc)

        if args['--unittest']:
            sys.argv.remove('--unittest')
            return runUnitTests()

        # Your code goes here...

        file2dump = args['FILE']
        file = open(file2dump) if file2dump else sys.stdin
        print hd(file.read(), int(args['--columns']), args['--header'])
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
                self.failUnlessEqual(hd('123', 4), '0000 | 31 32 33 .. | 123  |')
                self.failUnlessEqual(hd('1234', 4), '0000 | 31 32 33 34 | 1234 |')
                self.failUnlessEqual(hd('12345', 4), '0000 | 31 32 33 34 | 1234 |\n0004 | 35 .. .. .. | 5    |')

            def testCase_2(self):
                all = [chr(x) for x in xrange(254)]
                print '\n' + hd(all, header='All 256 chars')

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

        suites = unittest.TestSuite()
        suites.addTest(unittest.makeSuite(TestThis))
        #suites.addTest(unittest.makeSuite(TestThat))

        return unittest.TextTestRunner(verbosity=2).run(suites)

    sys.exit(main(sys.argv))
