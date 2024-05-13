#!/usr/bin/env python3

import json
import logging, logging.handlers

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

config = {} ###

logfilepath = '/Users/zarf/src/phogg/out.log'
loghandler = logging.handlers.WatchedFileHandler(logfilepath)
logging.basicConfig(
    format = '[%(levelname).1s %(asctime)s] %(message)s',
    datefmt = '%b-%d %H:%M:%S',
    level = logging.INFO,
    handlers = [ loghandler ],
)

appinstance = PhoggApp(config, [
    ('', han_Home),
    ('/api/getpics', han_GetPics),
    ('/api/settags', han_SetTags),
])

application = appinstance.application

if __name__ == '__main__':
    import phogglib.cli
    phogglib.cli.run(appinstance)


