import os, os.path
import time
import datetime
import uuid
import json
import subprocess
import logging

from phogglib.pic import Pic, parse_jpeg, parse_png
from phogglib.tag import Tag

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
                    (width, height, orient, timestr) = parse_jpeg(pathname)
                else:
                    continue
            except Exception as ex:
                logging.error('Failed to parse image (%s): %s', pathname, ex)
                continue

            timestamp = int(sta.st_mtime)
            if timestr:
                tup = time.strptime(timestr, '%Y:%m:%d %H:%M:%S')
                timestamp = int(time.mktime(tup))

            pictup = (guid, rpathname, filetype, width, height, orient, timestamp)
            pic = Pic(*pictup)
            logging.info('Adding %s to db', pic.pathname)
            curs.execute('INSERT INTO pics (guid, pathname, type, width, height, orient, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)', pictup)
            curs.execute('DELETE FROM assoc WHERE guid = ?', (guid,))

            #rawdat = datetime.datetime.fromtimestamp(pic.timestamp)
            #timedat = rawdat.astimezone(tz_utc)
            timedat = time.localtime(pic.timestamp)
            yeartag = time.strftime('year:%Y', timedat)
            monthtag = time.strftime('month:%Y-%b', timedat).lower()
            daytag = time.strftime('day:%Y-%b-%d', timedat).lower()
            
            curs.execute('INSERT INTO assoc (guid, tag) VALUES (?, ?)', (guid, yeartag))
            curs.execute('INSERT INTO assoc (guid, tag) VALUES (?, ?)', (guid, monthtag))
            curs.execute('INSERT INTO assoc (guid, tag) VALUES (?, ?)', (guid, daytag))
            newtags.add(yeartag)
            newtags.add(monthtag)
            newtags.add(daytag)
            
            subdir, _, _ = pic.pathname.rpartition('/')
            if subdir:
                dirtag = 'dir:'+subdir.lower()
                curs.execute('INSERT INTO assoc (guid, tag) VALUES (?, ?)', (guid, dirtag))
                newtags.add(dirtag)

    for tag in newtags:
        curs.execute('INSERT INTO tags (tag, autogen) VALUES (?, ?) ON CONFLICT DO NOTHING', (tag, True))

    res = curs.execute('SELECT guid, pathname FROM pics')
    ls = [ tup for tup in res.fetchall() ]
    for (guid, rpathname) in ls:
        if rpathname not in foundfiles:
            logging.info('Removing %s from db', rpathname)
            curs.execute('DELETE FROM pics WHERE guid = ?', (guid,))

def do_thumbnails(app):
    curs = app.getdb().cursor()
    
    res = curs.execute('SELECT guid, type, orient, pathname, thumbname FROM pics')
    ls = [ tup for tup in res.fetchall() ]

    for (guid, type, orient, pathname, thumbname) in ls:
        src = os.path.join(app.pic_path, pathname)
        dest = os.path.join(app.thumb_path, pathname)
        setdb = False
        if not os.path.exists(dest):
            logging.info('Creating thumbnail for %s', pathname)
            args = [ '/Users/zarf/src/phogg/thumbnail.py', src, dest, type, orient ]
            subprocess.run(args, check=True)
            setdb = True
        elif not thumbname:
            logging.info('Found thumbnail for %s', pathname)
            setdb = True
        if setdb:
            curs.execute('UPDATE pics SET thumbname = ? WHERE guid = ?', (pathname, guid,))
            
def do_exportfiles(app):
    curs = app.getdb().cursor()

    tagauto = dict()
    res = curs.execute('SELECT tag FROM tags where autogen = ?', (True,))
    for tup in res.fetchall():
        tagauto[tup[0]] = 1
    
    res = curs.execute('SELECT * FROM pics')
    picls = [ Pic(*tup) for tup in res.fetchall() ]
    picls.sort(key=lambda pic: (pic.timestamp, pic.pathname,))

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
        
def do_importfiles(app, filename):
    tagmap = dict()
    if filename.endswith('.json'):
        fl = open(filename)
        dat = json.load(fl)
        fl.close()
        for obj in dat['pics']:
            tagmap[obj['pathname']] = obj['tags']
    else:
        fl = open(filename)
        for ln in fl.readlines():
            if ln.startswith('#'):
                continue
            pic, _, tags = ln.partition(':')
            pic = pic.strip()
            if not pic:
                continue
            pic = pic.strip()
            tagls = [ val.strip() for val in tags.split(',') ]
            tagmap[pic] = tagls

    curs = app.getdb().cursor()
    
    res = curs.execute('SELECT tag FROM tags')
    tagset = set([ tup[0] for tup in res.fetchall() ])

    piccount = 0
    tagcount = 0
    
    for (pathname, tagls) in tagmap.items():
        res = curs.execute('SELECT * FROM pics WHERE pathname = ?', (pathname,))
        tup = res.fetchone()
        if not tup:
            print('no such image: %s' % (pathname,))
            continue
        pic = Pic(*tup)
        pic.fetchtags(app)
        
        didcount = 0
        for tag in tagls:
            if ':' in tag:
                continue
            if pic.tags and tag in pic.tags:
                continue
            didcount += 1
            curs.execute('INSERT INTO assoc (guid, tag) VALUES (?, ?)', (pic.guid, tag))
            if tag not in tagset:
                curs.execute('INSERT INTO tags (tag, autogen) VALUES (?, ?) ON CONFLICT DO NOTHING', (tag, False))
                tagset.add(tag)

        if didcount:
            tagcount += didcount
            piccount += 1
            
    logging.info('Imported %d tags for %d pics' % (tagcount, piccount,))
        

def do_generatepages(app):
    curs = app.getdb().cursor()

    tagauto = dict()
    res = curs.execute('SELECT tag FROM tags where autogen = ?', (True,))
    for tup in res.fetchall():
        tagauto[tup[0]] = 1
    
    res = curs.execute('SELECT * FROM pics')
    picls = [ Pic(*tup) for tup in res.fetchall() ]
    picls.sort(key=lambda pic: (pic.timestamp, pic.pathname,))

    imagesize = 180
    for pic in picls:
        pic.fetchtags(app)
        pic.tags.sort(key=lambda tag: (tagauto.get(tag, 0), tag))
        aspect = pic.width / pic.height
        if aspect > 1:
            pic.thumbwidth = imagesize
            pic.thumbheight = int(imagesize / aspect)
        else:
            pic.thumbheight = imagesize
            pic.thumbwidth = int(imagesize * aspect)

    tem = app.getjenv().get_template('cat.html')
    filename = os.path.join(app.webgen_path, 'index.html')
    fl = open(filename, 'w')
    fl.write(tem.render(pics=picls))
    fl.close()
    
