import devboard.utils as utils
import devboard.item as item


label_colors = (
    ('BC-', 'orange'),
    ('BC+', 'lime'),
    ('-', 'red'),
    ('+', 'green'),
    ('urgent', 'purple'),
    ('high', 'red'),
    ('medium', 'orange'),
    ('low', 'green'),
    ('', 'blue'),
)


class TrelloBoard(item.Item):
    pass


class TrelloList(item.Item):
    pass


class TrelloCard(item.Item):
    pass


class TrelloLabel(item.Item):
    pass


class Trello(object):
    name = 'trello'
    base_url = 'https://api.trello.com'

    def __init__(self, config):
        self.config = config

        self.board_dict = {}
        self.list_dict = {}
        self.card_dict = {}
        self.label_dict = {}
        self.list_boards = {}

    @property
    def _auth_string(self):
        auth = self.config.get('auth')
        return "?key={key}&token={token}".format(
            key=auth.get('key'), token=auth.get('token'))

    def _auth_params(self, d):
        auth = self.config.get('auth')
        d['key'] = auth.get('key')
        d['token'] = auth.get('token')

    def _boards(self):
        url = "{}/1/members/me/boards{}".format(
            self.base_url, self._auth_string)

        r = utils.get(url, ttl=10)

        self.board_dict = {
            b['name']: TrelloBoard(self, **b)
            for b in r
        }
        return self.board_dict

    def _labels(self, board_id):
        url = "{}/1/board/{}/labels{}".format(
            self.base_url, board_id, self._auth_string)

        r = utils.get(url, ttl=10)

        self.label_dict[board_id] = {
            li['name']: TrelloLabel(self, **li)
            for li in r
        }
        return self.label_dict[board_id]

    def _lists(self, board):
        self._labels(board.id)
        url = "{}/1/board/{}/lists{}".format(
            self.base_url, board.id, self._auth_string)

        r = utils.get(url, ttl=0, force=True)

        self.list_dict[board.id] = {
            li['name']: TrelloList(self, **li)
            for li in r
        }
        self.list_boards = {
            li['id']: board
            for li in r
        }
        return self.list_dict[board.id]

    def _cards(self, list_id):
        url = "{}/1/list/{}/cards{}&attachments=true".format(
            self.base_url, list_id, self._auth_string)

        cards = utils.get(url, ttl=10)

        self.card_dict[list_id] = {}
        for c in cards:
            url = "{}/1/card/{}/attachments{}".format(
                self.base_url, c['id'], self._auth_string)

            unique_id = None
            for a in c['attachments']:
                if a['name'] == 'devboardId':
                    unique_id = a['url'].split('/')[-1]

            if unique_id:
                self.card_dict[list_id][unique_id] = TrelloCard(
                    self, unique_id=unique_id, **c)

        return self.card_dict[list_id]

    def boards(self):
        return self._boards()

    def board_get(self, board_name):
        self._boards()
        return self.board_dict.get(board_name)

    def board_create(self, board_name):
        b = self.board_get(board_name)
        if b:
            return b

        params = {
            "name": board_name,
            "defaultLabels": "false",
            "defaultLists": "false",
            "keepFromSource": "none",
            "prefs_permissionLevel": "private",
            "prefs_voting": "disabled",
            "prefs_comments": "members",
            "prefs_invitations": "members",
            "prefs_selfJoin": "false",
            "prefs_cardCovers": "true",
            "prefs_background": "blue",
            "prefs_cardAging": "regular"
        }
        self._auth_params(params)

        url = "{}/1/boards/".format(self.base_url)

        r = utils.post(url, params=params)

        b = TrelloBoard(self, **r)
        self.board_dict[r['name']] = b
        return b

    def label_create(self, board_id, label_name):
        self._labels(board_id)
        if label_name in self.label_dict[board_id]:
            return self.label_dict[board_id][label_name]

        params = {
            "name": label_name,
            "idBoard": board_id
        }
        for pair in label_colors:
            li, c = pair
            if li in label_name:
                params['color'] = c
                break

        self._auth_params(params)

        url = "{}/1/labels".format(self.base_url)

        r = utils.post(url, params=params)

        li = TrelloLabel(self, **r)
        self.label_dict[board_id][r['name']] = li
        return li

    def lists(self, board):
        return self._lists(board)

    def list_get(self, board, list_name):
        self._lists(board)
        return self.list_dict[board.id].get(list_name)

    def list_create(self, board, list_name):
        li = self.list_get(board, list_name)
        if li:
            return li

        params = {
            "name": list_name,
            "idBoard": board.id
        }
        self._auth_params(params)

        url = "{}/1/lists".format(self.base_url)

        r = utils.post(url, params=params)

        li = TrelloList(self, **r)
        self.list_dict[board.id][r['name']] = li
        self.list_boards[li.id] = board
        return li

    def cards(self, li):
        return self._cards(li.id)

    def card_get(self, li, card_id):
        self._cards(li.id)
        cards = [
            c
            for c in self.card_dict[li.id].values()
            if c.unique_id == card_id
        ]
        if not cards:
            return None
        return cards[0]

    def card_delete(self, li, card_id):
        c = self.card_get(li, card_id)

        board = self.list_boards[li.id]

        new_list = self.list_create(board, 'Done')

        params = {
            "pos": 'top',
            "idList": new_list.id
        }
        self._auth_params(params)

        url = "{}/1/cards/{}".format(self.base_url, c.id)
        utils.put(url, params=params)

    def card_set(self, li, item):
        content = item.content[:4096]

        c = self.card_get(li, item.unique_id)
        if not c:
            params = {
                "name": item.summary,
                "desc": content,
                "pos": 'top',
                "idList": li.id,
            }
            self._auth_params(params)

            url = "{}/1/cards".format(self.base_url)
            r = utils.post(url, params=params)

            c = TrelloCard(self, unique_id=item.unique_id, **r)

            params = {
                "name": "devboardId",
                "url": "http://devboard/{}".format(item.unique_id)
            }
            self._auth_params(params)

            url = "{}/1/cards/{}/attachments".format(
                self.base_url, r['id'])
            r = utils.post(url, params=params)
        else:
            params = {}
            if c.name != item.summary:
                params['name'] = item.summary
            if c.desc != content:
                params['desc'] = content

            if params:
                params['pos'] = 'top'
                self._auth_params(params)

                url = "{}/1/cards/{}".format(self.base_url, c.id)
                r = utils.put(url, params=params)

        item_labels = []
        for tag in item.tags:
            board = self.list_boards[li.id]
            label = self.label_dict[board.id].get(tag)
            if not label:
                label = self.label_create(board.id, tag)
            item_labels.append(label)

        items_label_ids = [
            label.id
            for label in item_labels
        ]
        current_label_ids = [
            label['id']
            for label in c.labels
        ]

        for label in item_labels:
            if label.id not in current_label_ids:
                url = "{}/1/cards/{}/idLabels".format(
                    self.base_url, c.id)

                params = {
                    "value": label.id
                }
                self._auth_params(params)

                r = utils.post(url, params=params)

        for label in current_label_ids:
            if label not in items_label_ids:
                url = "{}/1/cards/{}/idLabels/{}".format(
                    self.base_url, c.id, label)

                params = {}
                self._auth_params(params)

                r = utils.delete(url, params=params)

        return c
