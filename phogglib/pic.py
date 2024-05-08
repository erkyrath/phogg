import os, os.path
import uuid
import pytz
import datetime

tz_utc = pytz.timezone('UTC')

class Pic:
    def __init__(self, guid, pathname, type, width, height, timestamp):
        self.guid = guid
        self.pathname = pathname
        self.type = type
        self.width = width
        self.height = height
        self.timestamp = timestamp

        dat = datetime.datetime.fromtimestamp(timestamp)
        dat = dat.astimezone(tz_utc)
        self.texttime = dat.strftime('%b %d, %Y')
        
    def tojson(self):
        return {
            'guid': self.guid,
            'pathname': self.pathname,
            'type': self.type,
            'width': self.width,
            'height': self.height,
            'timestamp': self.timestamp,
            'texttime': self.texttime,
        }

def do_scandir(app):
    curs = app.getdb().cursor()
    counter = 0
    
    for (dirpath, dirnames, filenames) in os.walk(app.pic_path):
        for filename in filenames:
            counter += 1
            pathname = os.path.join(dirpath, filename)
            rpathname = os.path.relpath(pathname, start=app.pic_path)
            
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
                elif suffix in ('.jpg', '.jpeg'):
                    filetype = 'jpeg'
                    (width, height) = parse_jpeg(pathname)
                else:
                    continue
            except Exception as ex:
                ### log somewhere?
                continue
            
            curs.execute('INSERT INTO pics (guid, pathname, type, width, height, timestamp) VALUES (?, ?, ?, ?, ?, ?)', (guid, rpathname, filetype, width, height, int(sta.st_mtime)))
            ### clear tags, add based on date and dir

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
        if (marker >= 0xC0 and marker <= 0xCF and marker != 0xC8):
            if clen <= 7:
                raise Exception('SOF block is too small')
            dat = list(fl.read(5))
            bits = dat[0]
            height = (dat[1] << 8) | dat[2]
            width  = (dat[3] << 8) | dat[4]
            fl.close()
            return (width, height)
        fl.seek(clen-2, os.SEEK_CUR)
    raise Exception('SOF block not found')

def bytes_to_intarray(dat):
    return [ val for val in dat ]

def intarray_to_bytes(arr):
    return bytes(arr)
    
