# Phogg: a simple photo tagging app

- Designed by Andrew Plotkin <erkyrath@eblong.com>

This is a very simple photo tagging web app. I use it to maintain my [personal photo collection][wwwphoto].

[wwwphoto]: https://eblong.com/zarf/photo/

The idea is that you hand it a directory full of photos. It shows them in a browser window. You can select photos (or groups of photos) and add tags. You can also search and browse by tag. That's all I need it to do, so that's all it does.

## Lack of install documentation

Phogg is a Python web app. You have to install it on a web server that supports [WSGI][] scripts.

[WSGI]: https://docs.python.org/3/library/wsgiref.html
[mod_wsgi]: https://pypi.org/project/mod-wsgi/

I'm afraid the install is not a documented procedure. I hacked it together on my Mac. So you know it's possible, which is the important part, right?

A couple of hints:

- For Apache, you have to enable the [`mod_wsgi`][mod_wsgi] module. 
- Steal the [`tinyapp`][tinyapp] module out of the [`ifarchive-admintool`][admintool] repository. (Yeah, I really need to split that out as its own project.)

[admintool]: https://github.com/iftechfoundation/ifarchive-admintool
[tinyapp]: https://github.com/iftechfoundation/ifarchive-admintool/tree/main/tinyapp

