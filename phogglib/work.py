import os, os.path
import time
import datetime
import uuid
import json
import subprocess
import logging
import feedgenerator

from phogglib.pic import Pic, parse_jpeg, parse_png
from phogglib.tag import Tag, tagfilename

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
        
def do_importfiles(app, filename, dryrun=False):
    tagmap = dict()
    titlemap = dict()
    if filename.endswith('.json'):
        fl = open(filename)
        dat = json.load(fl)
        fl.close()
        for obj in dat['pics']:
            tagmap[obj['pathname']] = obj['tags']
            if 'title' in obj:
                titlemap[obj['pathname']] = obj['title']
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

    if dryrun:
        for pic in tagmap:
            print(pic+' (tags):', ', '.join(tagmap[pic]))
        for pic in titlemap:
            print(pic+' (title):', titlemap[pic])
        return
    
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

    titlecount = 0
    
    for (pathname, title) in titlemap.items():
        curs.execute('UPDATE pics SET title = ? WHERE pathname = ?', (title, pathname,))
        titlecount += 1

    if titlecount:
        logging.info('Imported %d titles for pics' % (titlecount,))

def do_uploadpublic(app):
    curs = app.getdb().cursor()

    public = []
    res = curs.execute('SELECT guid FROM assoc WHERE tag = ?', ('public',))
    for tup in res.fetchall():
        public.append(tup[0])
    
    alreadysent = set()
    res = curs.execute('SELECT guid FROM assoc WHERE tag = ?', ('flag:uploaded',))
    for tup in res.fetchall():
        alreadysent.add(tup[0])

    curs.execute('INSERT INTO tags (tag, autogen) VALUES (?, ?) ON CONFLICT DO NOTHING', ('flag:uploaded', True))

    args = app.upload_cmd.split(' ')
    genargs = [ val for val in args if val ]

    for guid in public:
        if guid in alreadysent:
            continue
        
        res = curs.execute('SELECT * FROM pics WHERE guid = ?', (guid,))
        tup = res.fetchone()
        pic = Pic(*tup)
        
        (dirname, filename) = os.path.split(pic.pathname)
        srcname = os.path.join(app.pic_path, pic.pathname)
        if not dirname:
            destname = 'pics'
        else:
            destname = 'pics/'+dirname
        args = [ val.replace('$1', srcname).replace('$2', destname) for val in genargs]
        subprocess.run(args, check=True)

        if pic.thumbname:
            (dirname, filename) = os.path.split(pic.thumbname)
            srcname = os.path.join(app.thumb_path, pic.thumbname)
            if not dirname:
                destname = 'thumbs'
            else:
                destname = 'thumbs/'+dirname
            args = [ val.replace('$1', srcname).replace('$2', destname) for val in genargs]
            subprocess.run(args, check=True)

        curs.execute('INSERT INTO assoc (guid, tag) VALUES (?, ?)', (guid, 'flag:uploaded'))
        
        print('...uploaded', pic.pathname)

    # See do_exportfiles()...
    tagauto = dict()
    res = curs.execute('SELECT tag FROM tags where autogen = ?', (True,))
    for tup in res.fetchall():
        tagauto[tup[0]] = 1
    
    res = curs.execute('SELECT * FROM pics')
    picls = [ Pic(*tup) for tup in res.fetchall() ]
    picls.sort(key=lambda pic: (pic.timestamp, pic.pathname,))

    for pic in picls:
        pic.fetchtags(app)

    dat = { 'pics': [ pic.tojson() for pic in picls if 'public' in pic.tags ] }
    for obj in dat['pics']:
        obj['tags'].remove('public')
        obj['tags'].remove('flag:uploaded')
    srcname = os.path.join(app.export_path, 'picmap-public.json')
    fl = open(srcname, 'w')
    json.dump(dat, fl, indent=2)
    fl.close()

    destname = 'picmap-public.json'
    args = [ val.replace('$1', srcname).replace('$2', destname) for val in genargs]
    subprocess.run(args, check=True)
    print('...uploaded', 'picmap-public.json')


prefixsort = {
    None: 0,
    '???': 1,
    'dir': 2,
    'year': 3,
    'month': 4,
    'day': 5,
    'flag': 6,
}

def do_generatepages(app):
    if not app.webgen_path:
        raise Exception('WebGen:BasePath not set in config')
    if not app.webgen_url:
        raise Exception('WebGen:BaseURL not set in config')
    
    curs = app.getdb().cursor()

    alltags = dict()
    res = curs.execute('SELECT tag, autogen FROM tags')
    for tup in res.fetchall():
        val = 1 if tup[1] else 0
        alltags[tup[0]] = val
    
    res = curs.execute('SELECT * FROM pics')
    picls = [ Pic(*tup) for tup in res.fetchall() ]
    picls.sort(key=lambda pic: (-pic.timestamp, pic.pathname,))

    imagesize = 180
    imagesizeone = 500
    for pic in picls:
        pic.singlename = 'photo_%s.html' % (pic.pathname.replace('/', '::'))
        pic.fetchtags(app)
        pic.tags.sort(key=lambda tag: (alltags.get(tag, 0), tag))
        aspect = pic.width / pic.height
        if aspect > 1:
            pic.thumbwidth = imagesize
            pic.thumbheight = int(imagesize / aspect)
            pic.framewidth = imagesizeone
            pic.frameheight = int(imagesizeone / aspect)
        else:
            pic.thumbheight = imagesize
            pic.thumbwidth = int(imagesize * aspect)
            pic.frameheight = imagesizeone
            pic.framewidth = int(imagesizeone * aspect)

    tagmap = {}
    for pic in picls:
        for tag in pic.tags:
            if tag not in tagmap:
                tagmap[tag] = []
            tagmap[tag].append(pic)

    taggroupmap = { None: [] }
    for (tag, autogen) in alltags.items():
        ftag = tagfilename(tag)
        if tag not in tagmap:
            # no pics, skip
            continue
        tagcount = len(tagmap[tag])
        if not autogen:
            taggroupmap[None].append( (tag, tag, tagcount) )
        else:
            prefix, _, subtag = tag.partition(':')
            if prefix not in taggroupmap:
                taggroupmap[prefix] = []
            taggroupmap[prefix].append( (tag, subtag, tagcount) )

    for prefix in taggroupmap:
        taggroupmap[prefix].sort()
    prefixes = list(taggroupmap.keys())
    prefixes.sort(key=lambda prefix: prefixsort.get(prefix, 1))

    alltaggroups = []
    for prefix in prefixes:
        ls = taggroupmap[prefix]
        alltaggroups.append( (prefix, ls) )
    
    tem = app.getjenv().get_template('cat.html')
    temone = app.getjenv().get_template('single.html')

    # The whole list
    filename = os.path.join(app.webgen_path, 'index.html')
    fl = open(filename, 'w')
    fl.write(tem.render(pics=picls, alltags=alltaggroups, totalcount=len(picls), picuri=app.pic_uri, thumburi=app.thumb_uri))
    fl.close()

    # The single-photo frames
    for pic in picls:
        filename = os.path.join(app.webgen_path, pic.singlename)
        fl = open(filename, 'w')
        fl.write(temone.render(pagetitle=pic.pathname, usehomelink=True, pic=pic, picuri=app.pic_uri, thumburi=app.thumb_uri))
        fl.close()

    # The tag pages
    for (tag, ls) in tagmap.items():
        ftag = tagfilename(tag)
        filename = os.path.join(app.webgen_path, 'tag_%s.html' % (ftag,))
        fl = open(filename, 'w')
        fl.write(tem.render(curtag=tag, pagetitle=tag, usehomelink=True, pics=ls, alltags=alltaggroups, totalcount=len(picls), picuri=app.pic_uri, thumburi=app.thumb_uri))
        fl.close()

    # The RSS feed
    baseurl = app.webgen_url
    if baseurl.endswith('/'):
        baseurl = baseurl[ : -1 ]
    commontags = [ tag for (tag, autogen) in alltags.items() if not autogen ]
    commontags.sort()
    feed = feedgenerator.Atom1Feed(
        title = app.webgen_title,
        description = app.webgen_desc,
        link = app.webgen_url,
        feed_url = baseurl + '/feed.xml',
        language = 'en',
        categories = commontags,
    )

    feedpicls = picls[ 0 : 4 ] ###
    for pic in feedpicls:
        feed.add_item(
            title = 'Photograph',
            description = pic.title if pic.title else 'Photo',
            link = baseurl + '/' + pic.singlename,
            author_name = "###self.ctx.config['ownername']",
            categories = pic.tags,
            pubdate = datetime.datetime.fromtimestamp(pic.timestamp),
        )

    filename = os.path.join(app.webgen_path, 'feed.xml')
    fl = open(filename, 'w')
    feed.write(fl, 'utf-8')
    fl.close()
