# Harvard's CS50x Final Project - WebChess

## Video

<https://www.youtube.com/watch?v=yc0KhkMDJqs>

## Description

WebChess is a simple, web-based [GUI](https://www.chessprogramming.org/GUI) to play against [UCI](https://en.wikipedia.org/wiki/Universal_Chess_Interface) chess engines. This project was originally inspired by my own [UCI](https://en.wikipedia.org/wiki/Universal_Chess_Interface)-compliant chess engine, [simPLY_chess](https://github.com/andrewharabor/simPLY_chess), which was written in Python. The intention was to create a more user-friendly way to play against [UCI](https://en.wikipedia.org/wiki/Universal_Chess_Interface) engines (which are typically command-line programs) without needing to actually download a chess [GUI](https://www.chessprogramming.org/GUI), which are usually fairly complex since they contain analyzation features beyond just a simple game of chess.

### app.py

`app.py` is the main file of the project. It uses [Flask](https://flask.palletsprojects.com/en/3.0.x/) to manage the web application itself by defining various routes and the methods to access them while also utilizing the [python-chess](https://python-chess.readthedocs.io/en/latest/) library. It is responsible for validating the move from the client, pushing it to the board, and running the process containing the chess engine, returning the engine's move in response to the client's request.  While the client does have its own board state, it is checked against the server's with each request. Should they differ, the client's board will be changed to that of the server's upon recieving the response, which is done to prevent the user from tampering with the JavaScript in their browser and modifying the game state.

### static/script.js

`script.js`, located in the `static` directory, contains the JavaScript that runs in the user's browser. It contains the client's board state using the [chess.js](https://github.com/jhlywa/chess.js) library and also provides client-side validation. It also is responsible for handling the board embedded on the web-page by the [chessboard.js](https://chessboardjs.com/) library including the drag-and-drop behavior of the pieces, the piece theme, and the highlighting of legal moves. After the user makes a move, it sends a request to the server to update the game-state and awaits the response. It implements a simple REST API to manage such communication.

### templates/layout.html

`layout.html`, located in the `templates` directory, defines the main format of the website. The [Jinja](https://jinja.palletsprojects.com/en/3.1.x/) templating engine allows this layout to be used for other pages on the site and keeps the look consistent. The [simple.css](https://simplecss.org/) framework is utilized for a simple but clean look.

### templates/index.html

`index.html`, located in the `templates` directory, defines the structure of the main page. It contains the form with the game setting options for the user and the play button to start a new game.

### templates/play.html

`play.html`, located in the `templates` directory, is responsible for displaying the chess game itself. It contains the board that the user interacts with from [chessboard.js](https://chessboardjs.com/) along with other features such as displaying the [PGN](https://en.wikipedia.org/wiki/Portable_Game_Notation) of the game. It runs the `script.js` file which initializes the client-side board state when the game first starsts.

### static/style.css

`style.css`, located in the `static` directory, contains a few custom CSS modifications atop the [simple.css](https://simplecss.org/) framework such as adjustments to the board size among a couple other text formatting changes.

### engines

The `engines` directory contains the executable files for the chess engines the user can play against, among which is my own `simPLY_chess.py` in addition to [Stockfish](https://stockfishchess.org/) and [Komodo](https://komodochess.com/). It also contains the `opening-books` directory which has a variety of [PolyGlot](https://www.chessprogramming.org/PolyGlot) [opening books](https://en.wikipedia.org/wiki/Chess_opening_book_(computers)) for the engine to use.

## Limitations

The main limitation with the current implementation of this project is that it only supports one game at a time. If multiple users access the website at the same time, they will modify the same game or even worse, one user will create a new game that resets that of another user. This is because no session information is tracked (including no login system) and the server is only made to keep track of one game-state and run one engine (which blocks the whole process while it calculutes its move). If I come back to this project in the future, this will be one of the utmost priorities.

Additionally, only a select-few engines are offered. Allowing the user to import their own chess engine is not supported, as it could expose the site to malicious files. Attempting to implement this feature would require an immense amount of time to ensure the security of the web-app and would ultimatly defeat the purpose of this project.
