#!/usr/bin/env python3

import json

from tinyapp.handler import ReqHandler
from tinyapp.constants import PLAINTEXT, HTML

from phogglib.phoggapp import PhoggApp
import phogglib.cli

class han_Home(ReqHandler):
    def do_get(self, req):
        self.app.scandir()
        return self.app.render('main.html', req)

class han_GetPics(ReqHandler):
    def do_get(self, req):
        req.set_content_type('text/json')
        yield(json.dumps({'foo':'bar'}))
    
config = {} ###

appinstance = PhoggApp(config, [
    ('', han_Home),
    ('/api/getpics', han_GetPics),
])

application = appinstance.application

if __name__ == '__main__':
    phogglib.cli.run(appinstance)

    
