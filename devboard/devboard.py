import argparse
import logging
import os
import sys
import time
import yaml

import importlib
import pkgutil

import devboard.output as output
import devboard.source as source
import devboard.trello as trello


logging.basicConfig(level=logging.DEBUG)


class App(object):

    module_types = (SOURCE, OUTPUT) = ('source', 'output')

    def __init__(self, config_file, auth_file):
        self.modules = {t: {}
                        for t in self.module_types}

        if not config_file:
            config_file = self._config_file('config.yml')
        if not auth_file:
            auth_file = self._config_file('auth.yml')

        self._read_config(config_file, auth_file)
        self._register_modules()

    def _config_dir(self):
        yield os.getcwd()
        yield os.path.expanduser("~/.config/devboard/")

    def _config_file(self, filename):
        for d in self._config_dir():
            path = os.path.join(d, filename)
            if os.path.exists(path):
                return path
        return None

    def register(self, module_type, module):
        self.modules[module_type][module.name] = module
        return module

    def get_module(self, module_type, name):
        return self.modules[module_type].get(name)

    def _register_modules(self):
        import devboard.sources
        import devboard.outputs

        def iter_namespace(ns_pkg):
            return pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + ".")

        def import_module(name):
            module = importlib.import_module(name)
            for e in dir(module):
                elem = getattr(module, e)
                if (isinstance(elem, type) and
                        issubclass(elem, source.Source) and
                        elem != source.Source):
                    self.register(self.SOURCE, elem)
                if (isinstance(elem, type) and
                        issubclass(elem, output.Output) and
                        elem != output.Output):
                    self.register(self.OUTPUT, elem)

        for finder, name, ispkg in iter_namespace(devboard.sources):
            import_module(name)

        for finder, name, ispkg in iter_namespace(devboard.outputs):
            import_module(name)

    def _read_config(self, config_file, auth_file):
        with open(config_file) as fp:
            self.config = yaml.safe_load(fp.read())
        with open(auth_file) as fp:
            self.auths = yaml.safe_load(fp.read())['auth']

        for t in ('sources', 'outputs'):
            for module in self.config[t]:
                auth_name = module.get('auth')
                if auth_name is None:
                    auth_name = module['name']
                auths = [a
                         for a in self.auths
                         if a['name'] == auth_name]
                if auths:
                    module['auth'] = auths[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', metavar='interval', dest='interval',
                        type=int, default=-1)
    parser.add_argument('-c', metavar='config_file',
                        dest='config_file', type=str)
    parser.add_argument('-a', metavar='auth_file',
                        dest='auth_file', type=str)

    args = parser.parse_args()

    app = App(config_file=args.config_file,
              auth_file=args.auth_file)

    outputs = []
    for c in app.config['outputs']:
        cls = app.get_module(App.OUTPUT, c['type'])
        if cls:
            o = cls(c)
            outputs.append(o)

    while True:
        for c in app.config['sources']:
            cls = app.get_module(App.SOURCE, c['type'])
            if cls:
                s = cls(c)
                items = s.get()

                for output in outputs:
                    output.set(c['name'], items)
            else:
                print("Cannot find module {}".format(c['type']))
        if args.interval < 0:
            break

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
