import argparse
import os, os.path

from phogglib.work import do_scandir, do_exportfiles, do_importfiles, do_thumbnails, do_generatepages, do_uploadpublic

def run(appinstance):
    popt = argparse.ArgumentParser(prog='phogg.wsgi')
    subopt = popt.add_subparsers(dest='cmd', title='commands')

    pcmd = subopt.add_parser('createdb', help='create database tables')
    pcmd.set_defaults(cmdfunc=cmd_createdb)
    
    pcmd = subopt.add_parser('scan', help='scan photo dir')
    pcmd.set_defaults(cmdfunc=cmd_scan)
    
    pcmd = subopt.add_parser('thumbnail', help='thumbnail db files')
    pcmd.set_defaults(cmdfunc=cmd_thumbnail)
    
    pcmd = subopt.add_parser('webgen', help='export static site')
    pcmd.set_defaults(cmdfunc=cmd_webgen)
    
    pcmd = subopt.add_parser('export', help='export db files')
    pcmd.set_defaults(cmdfunc=cmd_export)
    
    pcmd = subopt.add_parser('import', help='import tag data to db files')
    pcmd.add_argument('filename')
    pcmd.add_argument('-n', '--dry-run', action='store_true', dest='dryrun')
    pcmd.add_argument('--timestamps', action='store_true', dest='timestamps')
    pcmd.set_defaults(cmdfunc=cmd_import)
    
    pcmd = subopt.add_parser('publicize', help='push public photos out')
    pcmd.set_defaults(cmdfunc=cmd_publicize)
    
    pcmd = subopt.add_parser('cleantags', help='remove unused tags')
    pcmd.set_defaults(cmdfunc=cmd_cleantags)
    
    pcmd = subopt.add_parser('renametag', help='rename a tag')
    pcmd.add_argument('oldtag')
    pcmd.add_argument('newtag')
    pcmd.set_defaults(cmdfunc=cmd_renametag)
    
    args = popt.parse_args()

    if not args.cmd:
        popt.print_help()
        return

    args.cmdfunc(args, appinstance)


def cmd_createdb(args, app):
    curs = app.getdb().cursor()
    res = curs.execute('SELECT name FROM sqlite_master')
    tables = [ tup[0] for tup in res.fetchall() ]

    if 'pics' in tables:
        print('"pics" table exists')
    else:
        print('creating "pics" table...')
        curs.execute('CREATE TABLE pics(guid unique, pathname unique, type, width, height, orient, timestamp, thumbname, title)')

    if 'tags' in tables:
        print('"tags" table exists')
    else:
        print('creating "tags" table...')
        curs.execute('CREATE TABLE tags(tag unique, autogen)')

    if 'assoc' in tables:
        print('"assoc" table exists')
    else:
        print('creating "assoc" table...')
        curs.execute('CREATE TABLE assoc(guid, tag)')

def cmd_scan(args, app):
    app.scandir(force=True)
    
def cmd_webgen(args, app):
    print('exporting static pages to %s' % (app.webgen_path,))
    do_generatepages(app)
    
def cmd_export(args, app):
    print('exporting tag data to %s' % (app.export_path,))
    do_exportfiles(app)
    
def cmd_import(args, app):
    print('importing tag data from %s' % (args.filename,))
    do_importfiles(app, args.filename, timestamps=args.timestamps, dryrun=args.dryrun)
    
def cmd_publicize(args, app):
    print('uploading public photos...')
    do_uploadpublic(app)
    
def cmd_thumbnail(args, app):
    do_thumbnails(app)
    
def cmd_cleantags(args, app):
    curs = app.getdb().cursor()
    res = curs.execute('SELECT tag FROM tags')
    alltags = [ tag[0] for tag in res.fetchall() ]

    ### should also delete from assocs where guid is not in pics!

    removed = []
    for tag in alltags:
        res = curs.execute('SELECT guid FROM assoc WHERE tag = ?', (tag,))
        if not res.fetchone():
            removed.append(tag)

    if not removed:
        print('no unused tags')
        return

    print('removing %d tags: %s' % (len(removed), ', '.join(removed),))
    for tag in removed:
        curs.execute('DELETE FROM tags WHERE tag = ?', (tag,))
        
def cmd_renametag(args, app):
    curs = app.getdb().cursor()
    
    res = curs.execute('SELECT tag, autogen FROM tags WHERE tag = ?', (args.oldtag,))
    tup = res.fetchone()
    if not tup:
        print('no such tag: %s' % (args.oldtag,))
        return
    if tup[1]:
        print('tag is autogenerated: %s' % (args.oldtag,))
        return
    
    res = curs.execute('SELECT tag FROM tags WHERE tag = ?', (args.newtag,))
    if res.fetchone():
        print('tag already exists: %s' % (args.newtag,))
        return

    print('renaming tag %s to %s' % (args.oldtag, args.newtag,))
    curs.execute('UPDATE tags SET tag = ? WHERE tag = ?', (args.newtag, args.oldtag,))
    curs.execute('UPDATE assoc SET tag = ? WHERE tag = ?', (args.newtag, args.oldtag,))

