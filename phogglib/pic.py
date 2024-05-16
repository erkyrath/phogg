import os, os.path
import time

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
        self.texttime = time.strftime('%b %d, %Y', time.localtime(timestamp))

    def __repr__(self):
        return '<Pic "%s" %s>' % (self.pathname, self.guid,)

    def fetchtags(self, app, assoc=None):
        if assoc is None:
            curs = app.getdb().cursor()
            res = curs.execute('SELECT tag FROM assoc WHERE guid = ?', (self.guid,))
            ls = [ tup[0] for tup in res.fetchall() ]
        else:
            ls = assoc.get(self.guid, [])
            ls = list(ls)
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
        if self.thumbname:
            res['thumbname'] = self.thumbname
        return res

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
    timestamp = None
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
                if indextag == 0x132:
                    tagtype = (dat[pos+2] << 8) | dat[pos+3]
                    tagcount = (dat[pos+4] << 24) | (dat[pos+5] << 16) | (dat[pos+6] << 8) | dat[pos+7]
                    tagoffset = (dat[pos+8] << 24) | (dat[pos+9] << 16) | (dat[pos+10] << 8) | dat[pos+11]
                    val = dat[ tagoffset+6 : tagoffset+6+tagcount ]
                    if val[-1] == 0:
                        val = val[ : -1 ]
                    timestamp = val.decode()
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
            return (width, height, orimap[orientation], timestamp)
        fl.seek(clen-2, os.SEEK_CUR)
    raise Exception('SOF block not found')
