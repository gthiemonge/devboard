import datetime

import devboard.utils
from devboard.source import Source
from devboard.item import Item


class BugzillaItem(Item):
    property_mapping = {
        'update_time': 'last_change_time'
    }

    @property
    def tags(self):
        return {self.status,
                "p:{}".format(self.args['priority']),
                "s:{}".format(self.args['severity'])}

    @property
    def last_update(self):
        return datetime.datetime.strptime(
            self.args['last_change_time'],
            "%Y-%m-%dT%H:%M:%SZ")


class BugzillaSource(Source):
    name = "bugzilla"

    parameters = {
        "include_fields": [
            "id",
            "creation_time",
            "last_change_time",
            "cf_internal_whiteboard",
            "severity",
            "priority",
            "product",
            "version",
            "target_milestone",
            "target_release",
            "component",
            "assigned_to",
            "status",
            "resolution",
            "summary",
            "description"
        ],
    }

    def get(self):
        params = dict(self.parameters)
        params["api_key"] = self.config['auth']['api_key']

        # TODO: handle more than one query
        params.update(self.config['queries'][0])

        doc = devboard.utils.get(
            "{}/rest/bug".format(self.config['url']),
            params=params)

        bugs = doc['bugs']

        ret = []
        for bug in bugs:
            ret.append(BugzillaItem(self, **bug))

        return ret
