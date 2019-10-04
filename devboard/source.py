class Source(object):
    name = 'source'

    def __init__(self, config):
        self.config = config

    @property
    def unique_name(self):
        return self.config.get('name', self.name)
