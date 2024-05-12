import os, os.path
import uuid
import pytz
import datetime
import json
import subprocess

tz_utc = pytz.timezone('UTC')

class Pic:
    def __init__(self, guid, pathname, type, width, height, orient, timestamp, thumbname=None):
        self.guid = guid
        self.pathname = pathname
        self.type = type
        self.width = width
        self.height = height
        self.orient = orient  # NLRF
        self.timestamp = timestamp
        self.thumbname = None
        if thumbname:
            self.thumbname = thumbname

        self.tags = None

        dat = datetime.datetime.fromtimestamp(timestamp)
        dat = dat.astimezone(tz_utc)
        self.texttime = dat.strftime('%b %d, %Y')
        self.yeartag = dat.strftime('year:%Y')
        self.monthtag = dat.strftime('month:%Y-%b').lower()
        self.daytag = dat.strftime('day:%Y-%b-%d').lower()

        subdir, _, _ = pathname.rpartition('/')
        if subdir:
            self.dirtag = 'dir:'+subdir.lower()
        else:
            self.dirtag = None

    def __repr__(self):
        return '<Pic "%s" %s>' % (self.pathname, self.guid,)

    def fetchtags(self, app):
        curs = app.getdb().cursor()
        res = curs.execute('SELECT tag FROM assoc WHERE guid = ?', (self.guid,))
        ls = [ tup[0] for tup in res.fetchall() ]
        ls.sort()
        self.tags = ls
        
    def tojson(self):
        res = {
            'guid': self.guid,
            'pathname': self.pathname,
            'type': self.type,
            'width': self.width,
            'height': self.height,
            'timestamp': self.timestamp,
            'texttime': self.texttime,
        }
        if self.tags:
            res['tags'] = list(self.tags)
        return res

def do_scandir(app):
    newtags = set()
    
    curs = app.getdb().cursor()
    counter = 0
    foundfiles = set()
    
    for (dirpath, dirnames, filenames) in os.walk(app.pic_path):
        for filename in filenames:
            counter += 1
            pathname = os.path.join(dirpath, filename)
            rpathname = os.path.relpath(pathname, start=app.pic_path)
            foundfiles.add(rpathname)
            
            res = curs.execute('SELECT guid FROM pics WHERE pathname = ?', (rpathname,))
            tup = res.fetchone()
            if tup:
                continue

            guid = str(uuid.uuid1(clock_seq=counter))
            sta = os.stat(pathname)
            
            _, suffix = os.path.splitext(pathname)
            suffix = suffix.lower()

            try:
                if suffix == '.png':
                    filetype = 'png'
                    (width, height) = parse_png(pathname)
                    orient = 'N'
                elif suffix in ('.jpg', '.jpeg'):
                    filetype = 'jpeg'
                    (width, height, orient) = parse_jpeg(pathname)
                else:
                    continue
            except Exception as ex:
                ### log somewhere?
                continue

            pictup = (guid, rpathname, filetype, width, height, orient, int(sta.st_mtime))
            pic = Pic(*pictup)
            print('### adding %s' % (pic,)) ###log?
            curs.execute('INSERT INTO pics (guid, pathname, type, width, height, orient, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)', pictup)
            curs.execute('DELETE FROM assoc WHERE guid = ?', (guid,))
            
            curs.execute('INSERT INTO assoc (guid, tag) VALUES (?, ?)', (guid, pic.yeartag))
            curs.execute('INSERT INTO assoc (guid, tag) VALUES (?, ?)', (guid, pic.monthtag))
            curs.execute('INSERT INTO assoc (guid, tag) VALUES (?, ?)', (guid, pic.daytag))
            newtags.add(pic.yeartag)
            newtags.add(pic.monthtag)
            newtags.add(pic.daytag)
            if pic.dirtag:
                curs.execute('INSERT INTO assoc (guid, tag) VALUES (?, ?)', (guid, pic.dirtag))
                newtags.add(pic.dirtag)

    for tag in newtags:
        curs.execute('INSERT INTO tags (tag, autogen) VALUES (?, ?) ON CONFLICT DO NOTHING', (tag, True))

    res = curs.execute('SELECT guid, pathname FROM pics')
    ls = [ tup for tup in res.fetchall() ]
    for (guid, rpathname) in ls:
        if rpathname not in foundfiles:
            print('### removing %s' % (rpathname,)) ###log?
            curs.execute('DELETE FROM pics WHERE guid = ?', (guid,))

def do_thumbnails(app):
    curs = app.getdb().cursor()
    
    res = curs.execute('SELECT guid, type, pathname, thumbname FROM pics')
    ls = [ tup for tup in res.fetchall() ]

    for (guid, type, pathname, thumbname) in ls:
        src = os.path.join(app.pic_path, pathname)
        dest = os.path.join(app.thumb_path, pathname)
        if not os.path.exists(dest):
            args = [ '/Users/zarf/src/phogg/thumbnail.py', src, dest, type ]
            subprocess.run(args, check=True)
            print('### thumbnailing %s' % (pathname,)) ###log?
            
def do_exportfiles(app):
    curs = app.getdb().cursor()

    tagauto = dict()
    res = curs.execute('SELECT tag FROM tags where autogen = ?', (True,))
    for tup in res.fetchall():
        tagauto[tup[0]] = 1
    
    res = curs.execute('SELECT * FROM pics')
    picls = [ Pic(*tup) for tup in res.fetchall() ]
    picls.sort(key=lambda pic: pic.timestamp)

    for pic in picls:
        pic.fetchtags(app)

    fl = open(os.path.join(app.export_path, 'picmap.txt'), 'w')
    for pic in picls:
        tagls = list(pic.tags)
        tagls.sort(key=lambda tag: (tagauto.get(tag, 0), tag))
        fl.write(pic.pathname)
        fl.write(': ')
        fl.write(', '.join(tagls))
        fl.write('\n')
    fl.close()

    dat = { 'pics': [ pic.tojson() for pic in picls ] }
    fl = open(os.path.join(app.export_path, 'picmap.json'), 'w')
    json.dump(dat, fl, indent=2)
    fl.close()
        
def parse_png(pathname):
    fl = open(pathname, 'rb')
    sig = fl.read(8)
    if list(sig) != [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]:
        raise Exception('PNG signature does not match')
    while True:
        dat = list(fl.read(4))
        clen = (dat[0] << 24) | (dat[1] << 16) | (dat[2] << 8) | dat[3]
        ctyp = fl.read(4)
        #print('Chunk:', ctyp, 'len', clen)
        if ctyp == b'IHDR':
            dat = list(fl.read(4))
            width  = (dat[0] << 24) | (dat[1] << 16) | (dat[2] << 8) | dat[3]
            dat = list(fl.read(4))
            height = (dat[0] << 24) | (dat[1] << 16) | (dat[2] << 8) | dat[3]
            fl.close()
            return (width, height)
        fl.seek(clen+4, os.SEEK_CUR)
    raise Exception('No PNG header block found')

def parse_jpeg(pathname):
    fl = open(pathname, 'rb')
    orientation = 1
    orimap = 'NNNFFRLLRN'
    while True:
        if fl.read(1)[0] != 0xFF:
            raise Exception('marker is not FF')
        marker = fl.read(1)[0]
        while marker == 0xFF:
            marker = fl.read(1)[0]
        if marker == 0x01 or (marker >= 0xD0 and marker <= 0xD9):
            #print('FF%02X*' % (marker,))
            continue
        dat = list(fl.read(2))
        clen = (dat[0] << 8) | dat[1]
        #print('FF%02X, len %d' % (marker, clen))
        if (marker == 0xE1):
            dat = fl.read(clen-2)
            if dat[0:4] != b'Exif':
                continue
            indexcount = (dat[14] << 8) | dat[15]
            for ix in range(indexcount):
                pos = 16 + 12*ix
                indextag = (dat[pos] << 8) | dat[pos+1]
                if indextag == 0x0112:
                    tagtype = (dat[pos+2] << 8) | dat[pos+3]
                    tagcount = (dat[pos+4] << 24) | (dat[pos+5] << 16) | (dat[pos+6] << 8) | dat[pos+7]
                    #tagoffset = (dat[pos+8] << 24) | (dat[pos+9] << 16) | (dat[pos+10] << 8) | dat[pos+11]
                    orientation = dat[pos+9]
            continue
        if (marker >= 0xC0 and marker <= 0xCF and marker != 0xC8):
            if clen <= 7:
                raise Exception('SOF block is too small')
            dat = list(fl.read(5))
            bits = dat[0]
            height = (dat[1] << 8) | dat[2]
            width  = (dat[3] << 8) | dat[4]
            fl.close()
            if orientation in (6, 8):
                (width, height) = (height, width)
            return (width, height, orimap[orientation])
        fl.seek(clen-2, os.SEEK_CUR)
    raise Exception('SOF block not found')
