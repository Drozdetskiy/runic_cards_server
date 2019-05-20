import secrets
import json
import time

from game import Game

from aiohttp import web
import socketio


sio = socketio.AsyncServer()

factory = web.Application()

sio.attach(factory)

clients = []


class GameQueue:
    game_queue = {}

    @classmethod
    def _queue_clearing(cls):
        now = time.time()
        for game_hash, game in cls.game_queue:
            if now - game.created_at > ServerSettings.CRITICAL_QUEUE_TIME:
                del cls.game_queue[game_hash]

    @classmethod
    def add(cls, game_hash, game):
        cls.game_queue[game_hash] = game
        if len(cls.game_queue) > ServerSettings.CRITICAL_QUEUE_LENGTH:
            cls._queue_clearing()


class ServerSettings:
    HOST = 'localhost'
    PORT = 8081

    PLAYER_HASH = 8
    PLAYER_HASH_LEN = 11
    STATUS = {
        'in_search': 0,
        'found': 1,
        'start_game': 2,
        'error': 3
    }

    CRITICAL_QUEUE_LENGTH = 30
    CRITICAL_QUEUE_TIME = 3600


class WebGame(Game):
    def __init__(
            self,
            hash_player_1,
            hash_player_2,
            name_player_1='RunicGameFan1',
            name_player_2='RunicGameFan2',
    ):
        self.name_player_1 = name_player_1
        self.name_player_2 = name_player_2
        self.players = {
            hash_player_1: 1,
            hash_player_2: 2
        }
        self.rooms = {
            hash_player_1: None,
            hash_player_2: None
        }
        self.created_at = time.time()
        self.game_history = {}
        super().__init__()

    def next_turn(self, card_index, i, j, get_player=0):
        player_number = 1 if self.turn % 2 else 2
        if self.players[get_player] == player_number:
            super().next_turn(card_index, i, j, player_number)
        return True

    def get_rooms(self):
        return list(self.rooms.values())

    def _do_json(self):
        _res = super().json_repr
        _res["card_queue_1"] = list(range(len(_res["player_1_hand"])))
        _res["card_queue_2"] = list(range(len(_res["player_2_hand"])))
        _res["name_player_1"] = self.name_player_1
        _res["name_player_2"] = self.name_player_2
        return json.dumps(_res)

    @property
    def json_repr(self):
        return self.game_history.setdefault(self.turn, self._do_json())


class UrlGenerator:
    def __init__(self):
        self.hash_url = secrets.token_urlsafe()
        hash_player_1 = secrets.token_urlsafe(ServerSettings.PLAYER_HASH)
        hash_player_2 = secrets.token_urlsafe(ServerSettings.PLAYER_HASH)
        while hash_player_1 == hash_player_2:
            hash_player_2 = secrets.token_urlsafe(ServerSettings.PLAYER_HASH)
        self.hash_player_1 = hash_player_1
        self.hash_player_2 = hash_player_2

    def add_game_to_queue(self):
        GameQueue.add(
            self.hash_url,
            WebGame(
                hash_player_1=self.hash_player_1,
                hash_player_2=self.hash_player_2
            )
        )

    def data(self, player_number):
        return json.dumps(
            {
                "status": ServerSettings.STATUS['found'],
                "hash_url": self.hash_url,
                "hash_player": getattr(self, f'hash_player_{player_number}')
            }
        )


async def add_name(sid, message):
    client_info = json.loads(message)
    game = GameQueue.game_queue[client_info['hash_url']]
    setattr(
        game,
        f'name_player_{game.players[client_info["hash_player"]]}',
        client_info['name']
    )
    await sio.emit(
        'message',
        json.dumps({"status": ServerSettings.STATUS['start_game']}),
        room=sid,
        namespace='/host'
    )


async def game_connection(sid):
    partner = clients.pop()
    game_urls = UrlGenerator()
    game_urls.add_game_to_queue()
    await sio.emit(
        'message',
        game_urls.data(1),
        room=sid,
        namespace='/host'
    )
    await sio.emit(
        'message',
        game_urls.data(2),
        room=partner,
        namespace='/host'
    )


@sio.on('connect', namespace='/host')
async def on_connect(sid, environ):
    print('connection established')
    if clients and sid not in clients:
        await game_connection(sid)
    else:
        if sid not in clients:
            clients.append(sid)
        await sio.emit(
            'message',
            json.dumps({"status": ServerSettings.STATUS['in_search']}),
            room=sid,
            namespace='/host'
        )


@sio.on('disconnect', namespace='/host')
def on_disconnect(sid):
    if sid in clients:
        clients.remove(sid)


@sio.on('message', namespace='/host')
async def print_message(sid, message):
    try:
        await add_name(sid, message)
    except KeyError:
        await sio.emit(
            'message',
            json.dumps({"status": ServerSettings.STATUS['error']}),
            room=sid,
            namespace='/host'
        )


@sio.on('connect', namespace='/game')
def on_connect(sid, environ):
    print('connection established 2')


@sio.on('message', namespace='/game')
async def game_message(sid, message):
    hash_url = message[:-ServerSettings.PLAYER_HASH_LEN:]
    player_hash = message[-ServerSettings.PLAYER_HASH_LEN::]
    try:
        GameQueue.game_queue[hash_url].rooms[player_hash] = sid
        await sio.emit(
            'player_number',
            GameQueue.game_queue[hash_url].players[player_hash],
            room=sid,
            namespace='/game'
        )
        await sio.emit(
            'message',
            GameQueue.game_queue[hash_url].json_repr,
            room=sid,
            namespace='/game'
        )
    except KeyError:
        await sio.emit(
            'message',
            "error",
            room=sid,
            namespace='/game'
        )


@sio.on('turn', namespace='/game')
async def game_message(sid, message):
    player_turn = json.loads(message)
    hash_url = player_turn['hash_url'][:-ServerSettings.PLAYER_HASH_LEN:]
    confirmed_turn = GameQueue.game_queue[hash_url].next_turn(
        player_turn['card_index'],
        player_turn['i'],
        player_turn['j'],
        player_turn['hash_url'][-ServerSettings.PLAYER_HASH_LEN::]
    )
    if confirmed_turn:
        room1, room2 = GameQueue.game_queue[hash_url].get_rooms()
        await sio.emit(
            'message',
            GameQueue.game_queue[hash_url].json_repr,
            room=room1,
            namespace='/game'
        )
        await sio.emit(
            'message',
            GameQueue.game_queue[hash_url].json_repr,
            room=room2,
            namespace='/game'
        )


@sio.on('disconnect', namespace='/game')
def on_disconnect(sid):
    print('disconnect', sid)


# app.add_routes([web.get('/host', print_message)])
# app.add_routes([web.get('/game', game_message)])

web.run_app(factory, host=ServerSettings.HOST, port=ServerSettings.PORT)
