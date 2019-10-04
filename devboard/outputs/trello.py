import devboard.trello as trello
from devboard.output import Output


class TrelloOutput(Output):
    name = 'trello'

    def __init__(self, config):
        super(TrelloOutput, self).__init__(config)

        self.trello = trello.Trello(config)

        self.board = self.trello.board_get(config['board'])
        if not self.board:
            self.board = self.trello.board_create(config['board'])

    def set(self, list_name, item_list):
        li = self.trello.list_get(self.board, list_name)
        if not li:
            li = self.trello.list_create(self.board, list_name)

        item_ids = {i.unique_id for i in item_list}
        card_ids = {c_id for c_id in self.trello.cards(li)}

        card_ids_to_delete = card_ids - item_ids
        for card_id in card_ids_to_delete:
            self.trello.card_delete(li, card_id)

        # Insert cards in reverse order (from oldest to newest)
        for item in sorted(item_list, key=lambda e: e.last_update):
            self.trello.card_set(li, item)
