import argparse
import os, os.path

def run(appinstance):
    popt = argparse.ArgumentParser(prog='phogg.wsgi')
    subopt = popt.add_subparsers(dest='cmd', title='commands')

    popt_createdb = subopt.add_parser('createdb', help='create database tables')
    popt_createdb.set_defaults(cmdfunc=cmd_createdb)
    
    popt_scan = subopt.add_parser('scan', help='scan photo dir')
    popt_scan.set_defaults(cmdfunc=cmd_scan)
    
    popt_export = subopt.add_parser('export', help='export db files')
    popt_export.set_defaults(cmdfunc=cmd_export)
    
    popt_cleantags = subopt.add_parser('cleantags', help='remove unused tags')
    popt_cleantags.set_defaults(cmdfunc=cmd_cleantags)
    
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
        curs.execute('CREATE TABLE pics(guid unique, pathname unique, type, width, height, timestamp)')

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
    
def cmd_export(args, app):
    app.exportfiles()
    
def cmd_cleantags(args, app):
    curs = app.getdb().cursor()
    res = curs.execute('SELECT tag FROM tags')
    alltags = [ tag[0] for tag in res.fetchall() ]

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
        
          
