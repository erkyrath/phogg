import time
import os, os.path
import threading
import sqlite3

from jinja2 import Environment, FileSystemLoader, select_autoescape

from tinyapp.app import TinyApp, TinyRequest
from tinyapp.handler import ReqHandler
import tinyapp.auth

from phogglib.work import do_scandir

class PhoggApp(TinyApp):
    def __init__(self, config, hanclasses):
        TinyApp.__init__(self, hanclasses, wrapall=[])

        ###
        self.approot = '/phogg'
        self.pic_uri = '/testpics'
        self.thumb_uri = '/testthumb'
        self.db_path = '/Users/zarf/src/phogg/sql/phogg.db'
        self.template_path = '/Users/zarf/src/phogg/templates'
        self.pic_path = '/Users/zarf/src/phogg/testpics'
        self.thumb_path = '/Users/zarf/src/phogg/testthumb'
        self.export_path = '/Users/zarf/src/phogg/export'

        ###
        #self.pic_uri = '/realpics'
        #self.thumb_uri = '/realthumbs'
        #self.pic_path = '/Users/zarf/Pictures/ZarfPhone Depot'
        #self.thumb_path = '/Users/zarf/src/phogg/realthumbs'
        
        # Thread-local storage for various things which are not thread-safe.
        self.threadcache = threading.local()

    def getdb(self):
        """Get or create a sqlite3 db connection object. These are
        cached per-thread.
        (The sqlite3 module is thread-safe, but the db connection objects
        you get from it might not be shareable between threads. Depends on
        the version of SQLite installed, but we take no chances.)
        """
        db = getattr(self.threadcache, 'db', None)
        if db is None:
            db = sqlite3.connect(self.db_path)
            db.isolation_level = None   # autocommit
            self.threadcache.db = db
        return db

    def getjenv(self):
        """Get or create a jinja template environment. These are
        cached per-thread.
        """
        jenv = getattr(self.threadcache, 'jenv', None)
        if jenv is None:
            jenv = Environment(
                loader = FileSystemLoader(self.template_path),
                extensions = [
                ],
                autoescape = select_autoescape(),
                keep_trailing_newline = True,
            )
            jenv.globals['approot'] = self.approot
            self.threadcache.jenv = jenv
        return jenv

    def render(self, template, req, **params):
        tem = self.getjenv().get_template(template)
        # The requri is the absolute URI, excluding domain and #fragment.
        # The requri is de-escaped, which is what we want -- it will be
        # used for <form action="requri">.
        map = {
            'req': req,
            'requri': req.app.approot+req.env['PATH_INFO'],
            #'user': req._user,
        }
        if params:
            map.update(params)
        yield tem.render(**map)

    def scandir(self, force=False):
        ### timestamp check unless force (subdirs harder?)
        do_scandir(self)
