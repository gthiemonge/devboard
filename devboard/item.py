from jinja2 import Environment, FileSystemLoader


class Item(object):
    property_mapping = {}

    def __init__(self, source, **kwargs):
        self.source = source
        self.args = kwargs

    def __getattr__(self, name):
        mapped_attr = self.property_mapping.get(name, name)
        if mapped_attr in self.args:
            return self.args[mapped_attr]
        raise AttributeError(name)

    def __repr__(self):
        return '<{} {}>'.format(self.__class__.__name__, self.id)

    @property
    def content(self):
        env = Environment(
                loader=FileSystemLoader('templates/')
        )
        template = env.get_template("{}.j2".format(self.source.name))
        return template.render(item=self, source=self.source)

    @property
    def unique_id(self):
        return "{}-{}".format(self.source.unique_name, self.id)

    @property
    def tags(self):
        return []
