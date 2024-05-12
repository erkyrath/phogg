#!/usr/bin/env python3

import sys
import os, os.path
import subprocess

if len(sys.argv) < 4:
    print('usage: thumbnail.py src dest imagetype')
    sys.exit(-1)

srcpath = sys.argv[1]
destpath = sys.argv[2]
imagetype = sys.argv[3]

if imagetype not in ('png', 'jpeg'):
    print('image type not recognized: ' + imagetype)
    sys.exit(-1)

destdir = os.path.dirname(destpath)
if not destdir:
    destdir = '.'
if destdir and not os.path.exists(destdir):
    os.makedirs(destdir)

nonce = str(os.getpid())
tempfile1 = os.path.join(destdir, '__temp_%s_1.pnm' % (nonce,))
tempfile2 = os.path.join(destdir, '__temp_%s_2.pnm' % (nonce,))

if imagetype == 'jpeg':
    args = [ 'jpegtopnm', srcpath ]
    outfl = open(tempfile1, 'wb')
    subprocess.run(args, check=True, stdout=outfl)
    outfl.close()

    args = [ 'pnmscale', '-xysize', '500', '500', tempfile1 ]
    outfl = open(tempfile2, 'wb')
    subprocess.run(args, check=True, stdout=outfl)
    outfl.close()

    args = [ 'pnmtojpeg', tempfile2 ]
    outfl = open(destpath, 'wb')
    subprocess.run(args, check=True, stdout=outfl)
    outfl.close()

    os.remove(tempfile1)
    os.remove(tempfile2)
    
if imagetype == 'png':
    args = [ 'pngtopnm', srcpath ]
    outfl = open(tempfile1, 'wb')
    subprocess.run(args, check=True, stdout=outfl)
    outfl.close()

    args = [ 'pnmscale', '-xysize', '500', '500', tempfile1 ]
    outfl = open(tempfile2, 'wb')
    subprocess.run(args, check=True, stdout=outfl)
    outfl.close()

    args = [ 'pnmtopng', tempfile2 ]
    outfl = open(destpath, 'wb')
    subprocess.run(args, check=True, stdout=outfl)
    outfl.close()

    os.remove(tempfile1)
    os.remove(tempfile2)
    
    
