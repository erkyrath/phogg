
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
    
