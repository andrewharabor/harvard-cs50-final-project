# python-chess: https://python-chess.readthedocs.io/en/latest/
# Flask: https://flask.palletsprojects.com/en/3.0.x/

from enum import StrEnum
from random import randint
from time import sleep

from chess import STARTING_FEN, Board
from chess.engine import Limit, SimpleEngine
from chess.polyglot import open_reader  # type: ignore
from flask import Flask, redirect, render_template, request

app = Flask(__name__)

class Error(StrEnum):
    INVALID_CONTENT_TYPE = "invalid_content_type"
    MISSING_MOVE = "missing_move"
    INVALID_MOVE = "invalid_move"

    def __str__(self) -> str:
        if self == Error.INVALID_CONTENT_TYPE:
            return "Expected application/json content type"
        elif self == Error.MISSING_MOVE:
            return "Expected move in request body"
        elif self == Error.INVALID_MOVE:
            return "Invalid user move"
        else:
            raise ValueError("Unknown Error StrEnum value")


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/play", methods=["GET", "POST"])
def play():
    global board, engine, book_path, time_limit

    if request.method == "POST":
        board = Board(STARTING_FEN)

        piece_theme = request.form.get("piece-theme", "neo")

        color = request.form.get("color", "random")
        if color == "random":
            color = ["white", "black"][randint(0, 100) % 2]

        opponent = request.form.get("engine", "stockfish")
        if opponent == "simPLY_chess":
            engine = SimpleEngine.popen_uci(r"engines/simPLY_chess.py")
        elif opponent == "komodo":
            engine = SimpleEngine.popen_uci(r"engines/komodo14")
        else:
            engine = SimpleEngine.popen_uci(r"engines/stockfish16")

        opening_book = request.form.get("opening-book", "no-book")
        if opening_book == "no-book":
            book_path = None
        else:
            book_path = r"engines/opening-books/" + opening_book

        time = request.form.get("think-time", "1")
        try:
            time_limit = int(time)
        except ValueError:
            time_limit = 1

        return render_template("play.html", engine=engine.id["name"], position=board.fen(en_passant="fen"), orientation=color, theme=piece_theme)  # type: ignore

    return redirect("/")


@app.route("/move", methods=["POST"])
def move():
    global board

    if request.content_type != 'application/json':
        return error_response(Error.INVALID_CONTENT_TYPE), 400

    request_body = request.get_json()

    client_san_move = request_body.get("move")
    if client_san_move is None:
        if (board.fen(en_passant="fen") == STARTING_FEN and board.ply() == 0):  # type: ignore
            return {"move": server_turn(), "fen": board.fen(en_passant="fen")}  # type: ignore

        return error_response(Error.MISSING_MOVE), 400

    client_move = board.parse_san(client_san_move)
    if client_move not in board.legal_moves:
        response =  error_response(Error.INVALID_MOVE)
        response["fen"] = board.fen(en_passant="fen")  # type: ignore
        return response, 400

    board.push(client_move)  # type: ignore
    return {"move": server_turn(), "fen": board.fen(en_passant="fen")}  # type: ignore

def server_turn() -> None | str:
    global board, engine, book_path, time_limit

    if board.is_game_over():
        return None

    move_object = None
    if book_path is not None:
        with open_reader(book_path) as reader:
            try:
                move_object = reader.weighted_choice(board).move
            except IndexError:
                move_object = None

    if move_object is None:
        move_object = engine.play(board, Limit(time=time_limit, depth=30)).move
    else:
        sleep(0.1)

    server_move = board.san(move_object)  # type: ignore
    board.push(move_object)  # type: ignore
    return server_move

def error_response(error: Error) -> dict[str, str]:
    return {"error_code": error.value, "error_msg": str(error)}
