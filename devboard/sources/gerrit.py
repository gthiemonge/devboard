import datetime

from devboard.source import Source
from devboard.item import Item
import devboard.utils


class GerritItem(Item):
    property_mapping = {
        'summary': 'subject'
    }

    def _label(self, label_name, shortname):
        ret = set()
        for cr in self.args['labels'].get(label_name, {}).get('all', []):
            if 'value' in cr and cr['value'] != 0:
                ret.add("{}{}{}".format(
                    shortname,
                    '+' if cr['value'] > 0 else '',
                    cr['value']))
        return ret

    def _code_review(self):
        return self._label('Code-Review', 'CR')

    def _verified(self):
        return self._label('Verified', 'V')

    def _workflow(self):
        return self._label('Workflow', 'W')

    def _backport_candidate(self):
        return self._label('Backport-Candidate', 'BC')

    @property
    def tags(self):
        return (self._code_review() | self._verified() |
                self._workflow() | self._backport_candidate())

    @property
    def last_update(self):
        return datetime.datetime.strptime(
            self.args['updated'][:19], "%Y-%m-%d %H:%M:%S")


class GerritSource(Source):
    name = "gerrit"

    def __init__(self, config):
        super(GerritSource, self).__init__(config)

        self.auth = None
        if 'auth' in config:
            self.auth = (config['auth'].get('username', ''),
                         config['auth'].get('password', ''))

        self.verify = config.get('verify', True)

    def get(self):
        url = '{}/changes/?q={}&n=50'.format(
            self.config['url'], '+'.join(self.config['queries'][0]['filter']))
        changes = devboard.utils.get(url, auth=self.auth,
                                     verify=self.verify, ttl=30)

        ret = []
        for c in changes:
            updated = datetime.datetime.strptime(
                c['updated'][:19], "%Y-%m-%d %H:%M:%S")

            detail = devboard.utils.get(
                '{}/changes/{}/detail'.format(self.config['url'],
                                              c['_number']),
                auth=self.auth,
                verify=self.verify,
                ttl=0,
                not_before=updated)

            ret.append(GerritItem(self, **detail))
        return ret
