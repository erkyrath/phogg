#!/usr/bin/env python3

from tinyapp.handler import ReqHandler
from tinyapp.constants import PLAINTEXT, HTML

from phogglib.phoggapp import PhoggApp

class han_Home(ReqHandler):
    def do_get(self, req):
        return self.app.render('main.html', req)

config = {} ###

appinstance = PhoggApp(config, [
    ('', han_Home),
])

application = appinstance.application

if __name__ == '__main__':
    print('### ok')
    
