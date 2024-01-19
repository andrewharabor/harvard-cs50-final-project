// chess.js: https://github.com/jhlywa/chess.js
// chessboard.js: https://chessboardjs.com/

const CHESSCOM_THEMES = ["3d_staunton", "3d_plastic", "3d_wood", "8_bit", "alpha", "bases", "book", "bubblegum",
    "cases", "classic", "club", "condal", "dash", "game_room", "glass", "gothic", "graffiti",
    "icy_sea", "light", "lolz", "luca", "marble", "maya", "metal", "modern", "nature", "neon",
    "neo", "neo_wood", "newspaper", "ocean", "sky", "space", "tigers", "tournament", "vintage",
    "wood"];

const LICHESS_THEMES = ["california", "cardinal", "cburnett", "celtic", "chess7", "chessnut", "companion",
    "dubrovny", "fantasy", "fresca", "gioco", "governor", "icpieces", "kiwen-suwi", "kosal",
    "leipzig", "libra", "maestro", "merida", "mpchess", "pirouetti", "pixel", "riohacha",
    "spatial", "staunty", "tatiana"];

const IMAGES_PATH = "static/images";
var chosenTheme = "neo";

var config;
var board;
var game;

var lightSquareGray = '#a9a9a9'
var darkSquareGray = '#696969'

function initialize(position, orientation, theme) {
    chosenTheme = theme;

    config = {
        draggable: true,
        onDragStart: onDragStart,
        onDrop: onDrop,
        onSnapEnd: onSnapEnd,
        orientation: orientation,
        pieceTheme: pieceTheme,
        position: position,
        showErrors: "alert",
    };

    board = Chessboard("board", config);
    game = new Chess();

    if (orientation === "black") {
        serverTurn(null);
    }

    return;
}

function onDragStart(source, piece, position, orientation) {
    if (game.game_over() || !orientation.startsWith(game.turn()) || !piece.startsWith(orientation[0])) {
        return false;
    }

    var moves = game.moves({
        square: source,
        verbose: true
    })

    if (moves.length !== 0) {
        for (var i = 0; i < moves.length; i++) {
            highlight(moves[i].to)
        }
    }

    return true;
}

function onDrop(source, target) {
    removeHighlights();

    const move = game.move({
        from: source,
        to: target,
        promotion: "q"
    });

    if (move === null) {
        return "snapback";
    }

    document.getElementById("pgn").innerHTML = game.pgn();

    displayError("");

    serverTurn(move.san);

    return "";
}

function onSnapEnd() {
    board.position(game.fen());

    return;
}

function pieceTheme(piece) {

    if (LICHESS_THEMES.includes(chosenTheme)) {
        format = ".svg";
    } else {
        format = ".png";
    }

    piece = piece.toLowerCase();
    if (piece[1] !== "p") {
        piece = piece[0] + piece[1].toUpperCase();
    }

    return IMAGES_PATH + "/" + chosenTheme + "/" + piece + format;
}

function removeHighlights() {
    $('#board .square-55d63').css('background', '')

    return;
}

function highlight(square) {
    var $square = $('#board .square-' + square)

    var background = lightSquareGray
    if ($square.hasClass('black-3c85d')) {
        background = darkSquareGray
    }

    $square.css('background', background)

    return;
}

async function serverTurn(san_move) {
    const rawResponse = await fetch("/move", {
        method: "POST",
        headers: {
            "Accept": "application/json",
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ "move": san_move })
    });

    if (rawResponse.status >= 500) {
        displayError("Server unavailable, try again later");
        game.undo();
    } else if (rawResponse.status >= 400) {
        const data = await rawResponse.json();
        if (data.error_code === "invalid_move") {
            game.load(data.fen);
            displayError(data.error_msg);
        } else {
            displayError("Incompatible client, refresh the page");
        }
    } else {
        const data = await rawResponse.json();
        game.move(data.move);
        document.getElementById("pgn").innerHTML = game.pgn();
        if (game.game_over()) {
            document.getElementById("status").innerHTML = "Game Over";
        }
    }

    window.setTimeout(() => { board.position(game.fen()) }, 100);
}

function displayError(msg) {
    document.getElementById("error").innerHTML = msg;
}
