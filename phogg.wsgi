#!/usr/bin/env python3

import os
import json
import logging, logging.handlers
import configparser
import threading

from tinyapp.handler import ReqHandler
from tinyapp.constants import PLAINTEXT, HTML

from phogglib.phoggapp import PhoggApp
from phogglib.pic import Pic
from phogglib.tag import Tag

class han_Home(ReqHandler):
    def do_get(self, req):
        self.app.scandir()
        return self.app.render('main.html', req,
                               pic_uri=json.dumps(self.app.pic_uri),
                               thumb_uri=json.dumps(self.app.thumb_uri))

class han_GetPics(ReqHandler):
    def do_get(self, req):
        curs = self.app.getdb().cursor()

        res = curs.execute('SELECT * FROM tags')
        tagls = [ Tag(*tup) for tup in res.fetchall() ]
        
        res = curs.execute('SELECT * FROM pics')
        picls = [ Pic(*tup) for tup in res.fetchall() ]

        assoc = dict()
        res = curs.execute('SELECT guid, tag FROM assoc')
        for (guid, tag) in res.fetchall():
            if guid not in assoc:
                assoc[guid] = [ tag ]
            else:
                assoc[guid].append(tag)

        for pic in picls:
            pic.fetchtags(self.app, assoc=assoc)
        
        req.set_content_type('text/json')
        dat = {
            'pics': [ pic.tojson() for pic in picls ],
            'tags': [ tag.tojson() for tag in tagls ],
        }
        yield(json.dumps(dat))

class han_SetTags(ReqHandler):
    def do_post(self, req):
        tag = req.get_input_field('tag')
        flag = (req.get_input_field('flag') == 'true')
        # Not sure where the '[]' comes from -- jQuery?
        guids = req.input.get('guids[]')

        curs = self.app.getdb().cursor()
        res = curs.execute('SELECT * FROM tags WHERE tag = ?', (tag,))
        tup = res.fetchone()
        if not tup:
            tup = (tag, False)
            curs.execute('INSERT INTO tags (tag, autogen) VALUES (?, ?)', tup)
        tag = Tag(*tup)

        resguids = []
        for guid in guids:
            res = curs.execute('SELECT * FROM assoc WHERE guid = ? AND tag = ?', (guid, tag.tag,))
            tup = res.fetchone()
            if flag:
                if not tup:
                    curs.execute('INSERT INTO assoc (guid, tag) VALUES (?, ?)', (guid, tag.tag,))
                    resguids.append(guid)
            else:
                if tup:
                    curs.execute('DELETE FROM assoc WHERE guid = ? AND tag = ?', (guid, tag.tag))
                    resguids.append(guid)

        if not resguids:
            dat = { 'error': 'no pictures selected' }
            yield(json.dumps(dat))
            return
        
        dat = {
            'tag': tag.tojson(),
            'flag': flag,
            'guids': resguids,
        }
        yield(json.dumps(dat))

class han_SetTitle(ReqHandler):
    def do_post(self, req):
        guid = req.get_input_field('guid')
        title = req.get_input_field('title')

        if not title:
            title = ''
        title = title.strip()

        curs = self.app.getdb().cursor()
        res = curs.execute('SELECT title FROM pics WHERE guid = ?', (guid,))
        tup = res.fetchone()
        if not tup:
            dat = { 'error': 'no matching picture' }
            yield(json.dumps(dat))
            return

        curs.execute('UPDATE pics SET title = ? WHERE guid = ?', (title, guid,))
        dat = {
            'guid': guid,
            'title': title,
        }
        yield(json.dumps(dat))


# Create the master handler list.
handlers = [
    ('', han_Home),
    ('/api/getpics', han_GetPics),
    ('/api/settags', han_SetTags),
    ('/api/settitle', han_SetTitle),
]

appinstance = None
config = None
initlock = threading.Lock()

def create_appinstance(environ):
    """Read the configuration and create the TinyApp instance.
    
    We have to do this when the first application request comes in,
    because the config file location is stored in the WSGI environment,
    which is passed in to application(). (It's *not* in os.environ,
    unless we're calling this from the command line.)
    """
    global config, appinstance

    with initlock:
        # To be extra careful, we do this under a thread lock. (I don't know
        # if application() can be called by two threads at the same time, but
        # let's assume it's possible.)
        
        if appinstance is not None:
            # Another thread did all the work while we were grabbing the lock!
            return
    
        # The config file contains all the paths and settings used by the app.
        # The location is specified by the PHOGG_CONFIG env var (if
        # on the command line) or the "SetEnv PHOGG_CONFIG" line (in the
        # Apache WSGI environment).
        configpath = '/opt/homebrew/var/wsgi-bin/phogg.config'
        configpath = environ.get('PHOGG_CONFIG', configpath)
        if not os.path.isfile(configpath):
            raise Exception('Config file not found: ' + configpath)
        
        config = configparser.ConfigParser()
        config.read(configpath)
        
        # Set up the logging configuration.
        # (WatchedFileHandler allows logrotate to rotate the file out from
        # under it.)
        logfilepath = config['DEFAULT']['LogFile']
        loghandler = logging.handlers.WatchedFileHandler(logfilepath)
        logging.basicConfig(
            format = '[%(levelname).1s %(asctime)s] %(message)s',
            datefmt = '%b-%d %H:%M:%S',
            level = logging.INFO,
            handlers = [ loghandler ],
        )
        
        # Create the application instance itself.
        appinstance = PhoggApp(config, handlers)

    # Thread lock is released when we exit the "with" block.


def application(environ, start_response):
    """The exported WSGI entry point.
    Normally this would just be appinstance.application, but we need to
    wrap that in order to call create_appinstance().
    """
    if appinstance is None:
        create_appinstance(environ)
    return appinstance.application(environ, start_response)


if __name__ == '__main__':
    import phogglib.cli
    create_appinstance(os.environ)
    phogglib.cli.run(appinstance)


