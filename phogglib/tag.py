import re

class Tag:
    def __init__(self, tag, autogen):
        self.tag = tag
        self.autogen = bool(autogen)

    def tojson(self):
        res = {
            'tag': self.tag,
            'autogen': self.autogen,
        }
        return res
    
pat_basictag = re.compile('^[a-zA-Z0-9: -]*$')
pat_fancychar = re.compile('[^a-zA-Z0-9:-]')

def escapefancy(match):
    ch = match.group(0)
    if ch == ' ':
        return '_'
    return '=%X=' % (ord(ch),)

def tagfilename(val):
    """Turn any string into an ASCII equivalent which can be used as a
    filename. (We don't want to worry about whether the filesystem supports
    UTF-8.)

    Different strings must always map to different strings; after that,
    human readability is nice. We don't have to reverse this mapping.
    """
    if not val:
        return '=='
    if pat_basictag.match(val):
        return val.replace(' ', '_')
    return pat_fancychar.sub(escapefancy, val)


