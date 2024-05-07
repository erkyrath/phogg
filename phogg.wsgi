#!/usr/bin/env python3

import json

from tinyapp.handler import ReqHandler
from tinyapp.constants import PLAINTEXT, HTML

from phogglib.phoggapp import PhoggApp
from phogglib.pic import Pic

class han_Home(ReqHandler):
    def do_get(self, req):
        self.app.scandir()
        return self.app.render('main.html', req)

class han_GetPics(ReqHandler):
    def do_get(self, req):
        curs = self.app.getdb().cursor()
        res = curs.execute('SELECT * FROM pics')
        picls = [ Pic(*tup) for tup in res.fetchall() ]
        
        req.set_content_type('text/json')
        dat = {
            'pics': [ pic.tojson() for pic in picls ],
        }
        yield(json.dumps(dat))
    
config = {} ###

appinstance = PhoggApp(config, [
    ('', han_Home),
    ('/api/getpics', han_GetPics),
])

application = appinstance.application

if __name__ == '__main__':
    import phogglib.cli
    phogglib.cli.run(appinstance)


