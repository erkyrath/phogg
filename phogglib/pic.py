import os, os.path
import uuid

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
                    dat = open(pathname, 'rb').read()
                    (width, height) = parse_png(dat)
                elif suffix in ('.jpg', '.jpeg'):
                    filetype = 'jpeg'
                    dat = open(pathname, 'rb').read()
                    (width, height) = parse_jpeg(dat)
                else:
                    continue
            except Exception as ex:
                ### log somewhere?
                continue
            
            print('### scandir:', rpathname, guid, width, height)

def parse_png(dat):
    dat = bytes_to_intarray(dat)
    pos = 0
    sig = dat[pos:pos+8]
    pos += 8
    if sig != [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]:
        raise Exception('PNG signature does not match')
    while pos < len(dat):
        clen = (dat[pos] << 24) | (dat[pos+1] << 16) | (dat[pos+2] << 8) | dat[pos+3]
        pos += 4
        ctyp = intarray_to_bytes(dat[pos:pos+4])
        pos += 4
        #print('Chunk:', ctyp, 'len', clen)
        if ctyp == b'IHDR':
            width  = (dat[pos] << 24) | (dat[pos+1] << 16) | (dat[pos+2] << 8) | dat[pos+3]
            pos += 4
            height = (dat[pos] << 24) | (dat[pos+1] << 16) | (dat[pos+2] << 8) | dat[pos+3]
            pos += 4
            return (width, height)
        pos += clen
        pos += 4
    raise Exception('No PNG header block found')

def parse_jpeg(dat):
    dat = bytes_to_intarray(dat)
    #print('Length:', len(dat))
    pos = 0
    while pos < len(dat):
        if dat[pos] != 0xFF:
            raise Exception('marker is not FF')
        while dat[pos] == 0xFF:
            pos += 1
        marker = dat[pos]
        pos += 1
        if marker == 0x01 or (marker >= 0xD0 and marker <= 0xD9):
            #print('FF%02X*' % (marker,))
            continue
        clen = (dat[pos] << 8) | dat[pos+1]
        #print('FF%02X, len %d' % (marker, clen))
        if (marker >= 0xC0 and marker <= 0xCF and marker != 0xC8):
            if clen <= 7:
                raise Exception('SOF block is too small')
            bits = dat[pos+2]
            height = (dat[pos+3] << 8) | dat[pos+4]
            width  = (dat[pos+5] << 8) | dat[pos+6]
            return (width, height)
        pos += clen
    raise Exception('SOF block not found')

def bytes_to_intarray(dat):
    return [ val for val in dat ]

def intarray_to_bytes(arr):
    return bytes(arr)
    
