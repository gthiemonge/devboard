import datetime
import re

from devboard.item import Item
from devboard.source import Source
from devboard.sources.gerrit import GerritItem
import devboard.utils


class GerritReviewItem(GerritItem):
    def need_review(self):
        if self.args['owner']['username'] == self.source.user:
            return False
        for cr in self.args['labels'].get('Code-Review', {}).get('all', []):
            if cr.get('username') == self.source.user and cr['value'] != 0:
                return False
        return True

    def _is_backport(self):
        branch = self.args.get('branch')
        if branch and branch != 'master':
            return {'backport'}
        return set()

    @property
    def tags(self):
        return ({self.review_tag} | self._code_review() | self._verified() |
                self._workflow() | self._backport_candidate() | self._is_backport())


class OctaviaPriorityReviews(Source):
    name = "octavia-priority-reviews"

    def __init__(self, config):
        super(OctaviaPriorityReviews, self).__init__(config)

        self.user = config.get('username')

    def get(self):
        url = "https://etherpad.openstack.org/p/octavia-priority-reviews/export/txt"

        content = devboard.utils.get(url)

        current_tag = None

        review_urls = {}
        id_tags = {}

        for line in content.split('\n'):
            line = line.strip()

            if not line:
                continue

            if line.startswith('*'):
                if line.endswith(' Priority Reviews:'):
                    current_tag = line[1:].split(' ')[0]
                else:
                    break
                continue

            m = re.search('(?P<base>https?://[^/]*)(/#/c)?'
                          '/(?P<id>[0-9]*)/?([ ]|$)',
                          line)
            if not m:
                continue

            d = m.groupdict()
            if d['base'] not in review_urls:
                review_urls[d['base']] = []
            review_urls[d['base']].append(d['id'])
            id_tags[int(d['id'])] = current_tag

        ret = []

        for base_url, ids in review_urls.items():

            url = '{}/changes/?q={}&n=100'.format(
                base_url, '+OR+'.join(ids))
            changes = devboard.utils.get(url, ttl=30)

            for c in changes:
                updated = datetime.datetime.strptime(
                    c['updated'][:19], "%Y-%m-%d %H:%M:%S")

                detail = devboard.utils.get(
                    '{}/changes/{}/detail'.format(base_url,
                                                  c['_number']),
                    ttl=0,
                    not_before=updated)

                orig_url = "{}/#/c/{}".format(base_url, c['_number'])
                tag = id_tags.get(c['_number'])
                item = GerritReviewItem(self, **detail, review_tag=tag,
                                        review_url=orig_url)
                if item.need_review():
                    ret.append(item)

        return ret
