from card_set import card_set
from random import randint


class WrongCell(Exception):
    pass


class CardLogic:
    COMPARE_QUEUE = (
        ('top', 'bot'),
        ('bot', 'top'),
        ('left', 'right'),
        ('right', 'left')
    )

    CARD_SIDE_QUEUE = (
        'top',
        'bot',
        'left',
        'right'
    )


class Card(CardLogic):
    def __init__(self, top=0, bot=0, left=0, right=0, player=0):
        self.top = top
        self.bot = bot
        self.left = left
        self.right = right
        self.player = player
        self.score = 0

    @property
    def json_repr(self):
        return {
            "top": self.top,
            "bot": self.bot,
            "left": self.left,
            "right": self.right,
            "player": self.player
        }

    def __add__(self, other):
        return tuple(
            map(
                lambda x: getattr(self, x[0]) + getattr(other, x[1]),
                self.COMPARE_QUEUE
            )
        ) if getattr(other, 'player', None) \
            else (-100, -200, -300, -400)

    def __sub__(self, other):
        return tuple(
            map(
                lambda x: getattr(self, x[0]) - getattr(other, x[1]),
                self.COMPARE_QUEUE
            )
        ) if getattr(other, 'player', None)\
                   else (-100, -200, -300, -400)

    def __repr__(self):
        return f'{self.top}-{self.bot}-' \
            f'{self.left}-{self.right}-__{self.player}__'


class Table:
    def __init__(self, side, plus=True, same=True, base_attack=True):
        self.side = side
        self.table = [[Card() for __ in range(side)] for _ in range(side)]
        self.mods = {
            'plus': plus,
            'same': same,
            'base_attack': base_attack
        }
        self.mods_queue = ('plus', 'same', 'base_attack')

    @property
    def json_repr(self):
        table_repr = []
        for row in self.table:
            for card in row:
                table_repr.append(card.json_repr)
        return table_repr

    def print_table(self):
        print('  ', end='')
        for i in range(self.side):
            print(f'      {i}        ', end='')
        print()
        for i in range(self.side):
            print(f'{i} {self.table[i]}')

    def place_card(self, i, j, card):
        if self.table[i][j].player:
            raise WrongCell

        self.table[i][j] = card
        return self.compare_cards(i, j, card)

    def compare_cards(self, i, j, card):
        for mod in self.mods_queue:
            if self.mods[mod]:
                score = getattr(self, f'_{mod}')(i, j, card)
                if score:
                    return score
        return 0

    def _same(self, i, j, card):
        score = 0
        _effected_card_list = list(
            filter(
                lambda x: x,
                (self.get_card(coord)
                 if not (card - self.get_card(coord))[index] else None
                 for index, coord in enumerate(self.neighbours[i, j]))
            )
        )

        if len(_effected_card_list) > 1:
            for attaked_card in _effected_card_list:
                if attaked_card.player != card.player:
                    attaked_card.player = card.player
                    score += 1
        return score

    def _plus(self, i, j, card):
        score = 0
        _coord_list = self.neighbours[i, j]
        _sum_list = [
            (card + self.get_card(coord))[index]
            for index, coord in enumerate(_coord_list)
        ]
        _coord_dict = {}

        for index, _sum in enumerate(_sum_list):
            attaked_card = self.get_card(_coord_list[index])

            if attaked_card:
                _coord_dict.setdefault(_sum, []).append(attaked_card)

        for key in _coord_dict.keys():
            if len(_coord_dict[key]) > 1:
                for attaked_card in _coord_dict[key]:
                    if attaked_card.player != card.player:
                        attaked_card.player = card.player
                        score += 1
        return score

    def _base_attack(self, i, j, card):
        score = 0
        _effected_card_list = list(
            filter(
                lambda x: x,
                (self.get_card(coord)
                 if (card - self.get_card(coord))[index] > 0 else None
                 for index, coord in enumerate(self.neighbours[i, j]))
            )
        )

        for attaked_card in _effected_card_list:
            if attaked_card.player != card.player:
                attaked_card.player = card.player
                score += 1
        return score

    @property
    def neighbours(self):
        _neighbours = []
        for i in range(self.side):
            for j in range(self.side):
                _neighbours.append(
                    [
                        (i, j),
                        (i - 1, j) if i - 1 >= 0 else None,
                        (i + 1, j) if i + 1 < self.side else None,
                        (i, j - 1) if j - 1 >= 0 else None,
                        (i, j + 1) if j + 1 < self.side else None
                    ]
                )

        return {x[0]: x[1:] for x in _neighbours}

    def get_card(self, *args):
        if args[0]:
            return self.table[args[0][0]][args[0][1]]


class Player:
    def __init__(self, number):
        self.number = number
        self.hand = [
            Card(*card_set['level_8'][randint(0, 3)], player=number),
            Card(*card_set['level_7'][randint(0, 3)], player=number),
            Card(*card_set['level_5'][randint(0, 3)], player=number),
            Card(*card_set['level_3'][randint(0, 3)], player=number),
            Card(*card_set['level_2'][randint(0, 3)], player=number),
        ]
        self.score = 5

    @property
    def json_repr(self):
        return [card.json_repr for card in self.hand]


class Game:
    def __init__(self, n=3, **kwargs):
        mods = kwargs
        self.table = Table(n, **mods)
        self.player_1 = Player(1)
        self.player_2 = Player(2)
        self.turn = 1

    def res(self):
        print(f'{self.player_1.number} '
              f'card_set{self.player_1.hand} '
              )
        print('#' * 20)
        self.table.print_table()
        print('#' * 20)

        print(f'{self.player_2.number} '
              f'card_set{self.player_2.hand} '
              )
        print(f'score_1: {self.player_1.score} '
              f'score_2: {self.player_2.score}'
              )

    @property
    def json_repr(self):
        return {
            "table": self.table.json_repr,
            "player_1_hand": self.player_1.json_repr,
            "player_2_hand": self.player_2.json_repr,
            "turn": self.turn,
            "player_1_score": self.player_1.score,
            "player_2_score": self.player_2.score,
        }

    def next_turn(self, card_index, i, j, get_player=0):
        if not get_player:
            player_number = 1 if self.turn % 2 else 2
        else:
            player_number = get_player

        card = getattr(self,
                       f'player_{player_number}'
                       ).hand.pop(card_index)
        _score = self.table.place_card(i, j, card)
        getattr(
            self,
            f'player_{1 if self.turn % 2 else 2}'
        ).score += _score
        getattr(
            self,
            f'player_{2 if self.turn % 2 else 1}'
        ).score -= _score
        self.turn += 1


def input_card():
    card_index = int(input('card_index = '))
    i = int(input('row = '))
    j = int(input('column = '))
    return card_index, i, j


def main():
    g = Game()
    print('Start Game')
    for _ in range(9):
        g.res()
        card_index, i, j = input_card()
        g.next_turn(card_index, i, j)
    g.res()


if __name__ == '__main__':
    main()
