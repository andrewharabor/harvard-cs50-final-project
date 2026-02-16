#!/usr/bin/env -S uv run --script

#########################################################################
# simPLY_chess, a simple chess engine written in Python                 #
# Copyright (C) 2023  Andrew Harabor                                    #
#                                                                       #
# This program is free software: you can redistribute it and/or modify  #
# it under the terms of the GNU General Public License as published by  #
# the Free Software Foundation, either version 3 of the License, or     #
# (at your option) any later version.                                   #
#                                                                       #
# This program is distributed in the hope that it will be useful,       #
# but WITHOUT ANY WARRANTY; without even the implied warranty of        #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         #
# GNU General Public License for more details.                          #
#                                                                       #
# You should have received a copy of the GNU General Public License     #
# along with this program.  If not, see <https://www.gnu.org/licenses/> #
#########################################################################

import itertools
import pathlib
import random
import struct
import sys
import time

NAME: str = "simPLY_chess"
AUTHOR: str = "andrewharabor"
VERSION: str = "3.3"

##################################
# CONSTANTS AND GLOBAL VARIABLES #
##################################

# Corner squares
A1: int = 91
H1: int = 98
A8: int = 21
H8: int = 28

# Cardinal directions
NORTH: int = -10
EAST: int = 1
SOUTH: int = 10
WEST: int = -1

# Directions for each piece type
PIECE_DIRECTIONS: dict[str, list[int]] = {
    "P": [NORTH, NORTH + NORTH, NORTH + WEST, NORTH + EAST],
    "N": [NORTH + NORTH + EAST, NORTH + NORTH + WEST, EAST + EAST + NORTH, EAST + EAST + SOUTH, SOUTH + SOUTH + EAST, SOUTH + SOUTH + WEST, WEST + WEST + SOUTH, WEST + WEST + NORTH],
    "B": [NORTH + EAST, SOUTH + EAST, SOUTH + WEST, NORTH + WEST],
    "R": [NORTH, EAST, SOUTH, WEST],
    "Q": [NORTH, EAST, SOUTH, WEST, NORTH + EAST, SOUTH + EAST, SOUTH + WEST, NORTH + WEST],
    "K": [NORTH, EAST, SOUTH, WEST, NORTH + EAST, SOUTH + EAST, SOUTH + WEST, NORTH + WEST]
}

# Initial board setup
# 10 x 12 board for easy detection of moves that go off the edge of the board
# Uppercase letters are used for the current player's pieces and lowercase letters are used for the opponent's pieces
# Periods are used for empty squares and spaces are used for off-board squares
INITIAL_POSITION: str = (
    "         \n"  # 0 - 9
    "         \n"  # 10 - 19
    " rnbqkbnr\n"  # 20 - 29
    " pppppppp\n"  # 30 - 39
    " ........\n"  # 40 - 49
    " ........\n"  # 50 - 59
    " ........\n"  # 60 - 69
    " ........\n"  # 70 - 79
    " PPPPPPPP\n"  # 80 - 89
    " RNBQKBNR\n"  # 90 - 99
    "         \n"  # 100 - 109
    "         \n"  # 110 - 119
)
INITIAL_CASTLING: list[bool] = [True, True]  # [queenside, kingside]
INITIAL_OPPONENT_CASTLING: list[bool] = [True, True]  # [queenside, kingside]
INITIAL_EN_PASSANT: int = 0  # square where en passant is possible for the current player
INITIAL_KING_PASSANT: int = 0  # square the king "passes through" when castling (the square the rook is moved to), used to detect castling through check
INITIAL_COLOR: str = "w"  # the current player's color

# Transposition table, used to store previously calculated positions and keep track of the best move
TRANSPOSITION_TABLE: dict[int, tuple[tuple[int, int, str, str], int, int]] = {}  # format is {zobrist_key: (best_move, depth, score)}

# Piece values, piece square tables, and tropism values for the middlegame and endgame
# Used to evaluate the position in terms of material and piece placement, and king safety
MIDGAME_PAWN_VALUE: int = 100  # all values are in centipawns
MIDGAME_KNIGHT_VALUE: int = 411
MIDGAME_BISHOP_VALUE: int = 445
MIDGAME_ROOK_VALUE: int = 582
MIDGAME_QUEEN_VALUE: int = 1250
MIDGAME_KING_VALUE: int = 100000

MIDGAME_PIECE_VALUES: dict[str, int] = {
    "P": MIDGAME_PAWN_VALUE,
    "N": MIDGAME_KNIGHT_VALUE,
    "B": MIDGAME_BISHOP_VALUE,
    "R": MIDGAME_ROOK_VALUE,
    "Q": MIDGAME_QUEEN_VALUE,
    "K": MIDGAME_KING_VALUE
}

MIDGAME_TROPISM_VALUES: dict[str, int] = {piece: value // 5 for piece, value in MIDGAME_PIECE_VALUES.items()}


MIDGAME_PAWN_TABLE: list[int] = [
       0,    0,    0,    0,    0,    0,    0,    0,
     120,  163,   74,  116,   83,  154,   41,  -13,
      -7,    9,   32,   38,   79,   68,   30,  -24,
     -17,   16,    7,   26,   28,   15,   21,  -28,
     -33,   -2,   -6,   20,   26,    7,   12,  -30,
     -32,   -5,   -5,  -12,    4,    4,   40,  -15,
     -43,   -1,  -24,  -33,  -23,   29,   46,  -27,
       0,    0,    0,    0,    0,    0,    0,    0,
]

MIDGAME_KNIGHT_TABLE: list[int] = [
    -204, -109,  -41,  -60,   74, -118,  -18, -130,
     -89,  -50,   88,   44,   28,   76,    9,  -21,
     -57,   73,   45,   79,  102,  157,   89,   54,
     -11,   21,   23,   65,   45,   84,   22,   27,
     -16,    5,   20,   16,   34,   23,   26,  -10,
     -28,  -11,   15,   12,   23,   21,   30,  -20,
     -35,  -65,  -15,   -4,   -1,   22,  -17,  -23,
    -128,  -26,  -71,  -40,  -21,  -34,  -23,  -28,
]

MIDGAME_BISHOP_TABLE: list[int] = [
     -35,    5, -100,  -45,  -30,  -51,    9,  -10,
     -32,   20,  -22,  -16,   37,   72,   22,  -57,
     -20,   45,   52,   49,   43,   61,   45,   -2,
      -5,    6,   23,   61,   45,   45,    9,   -2,
      -7,   16,   16,   32,   41,   15,   12,    5,
       0,   18,   18,   18,   17,   33,   22,   12,
       5,   18,   20,    0,    9,   26,   40,    1,
     -40,   -4,  -17,  -26,  -16,  -15,  -48,  -26,
]

MIDGAME_ROOK_TABLE: list[int] = [
      39,   51,   39,   62,   77,   11,   38,   52,
      33,   39,   71,   76,   98,   82,   32,   54,
      -6,   23,   32,   44,   21,   55,   74,   20,
     -29,  -13,    9,   32,   29,   43,  -10,  -24,
     -44,  -32,  -15,   -1,   11,   -9,    7,  -28,
     -55,  -30,  -20,  -21,    4,    0,   -6,  -40,
     -54,  -20,  -24,  -11,   -1,   13,   -7,  -87,
     -23,  -16,    1,   21,   20,    9,  -45,  -32,
]

MIDGAME_QUEEN_TABLE: list[int] = [
     -34,    0,   35,   15,   72,   54,   52,   55,
     -29,  -48,   -6,    1,  -20,   70,   34,   66,
     -16,  -21,    9,   10,   35,   68,   57,   70,
     -33,  -33,  -20,  -20,   -1,   21,   -2,    1,
     -11,  -32,  -11,  -12,   -2,   -5,    4,   -4,
     -17,    2,  -13,   -2,   -6,    2,   17,    6,
     -43,  -10,   13,    2,   10,   18,   -4,    1,
      -1,  -22,  -11,   12,  -18,  -30,  -38,  -61,
]

MIDGAME_KING_TABLE: list[int] = [
     -79,   28,   20,  -18,  -68,  -41,    2,   16,
      35,   -1,  -24,   -9,  -10,   -5,  -46,  -35,
     -11,   29,    2,  -20,  -24,    7,   27,  -27,
     -21,  -24,  -15,  -33,  -37,  -30,  -17,  -44,
     -60,   -1,  -33,  -48,  -56,  -54,  -40,  -62,
     -17,  -17,  -27,  -56,  -54,  -37,  -18,  -33,
       1,    9,  -10,  -78,  -52,  -20,   11,   10,
     -18,   44,   15,  -66,   10,  -34,   29,   17,
]

MIDGAME_PIECE_SQUARE_TABLES: dict[str, list[int]] = {
    "P": MIDGAME_PAWN_TABLE,
    "N": MIDGAME_KNIGHT_TABLE,
    "B": MIDGAME_BISHOP_TABLE,
    "R": MIDGAME_ROOK_TABLE,
    "Q": MIDGAME_QUEEN_TABLE,
    "K": MIDGAME_KING_TABLE,
}

ENDGAME_PAWN_VALUE: int = 115
ENDGAME_KNIGHT_VALUE: int = 343
ENDGAME_BISHOP_VALUE: int = 362
ENDGAME_ROOK_VALUE: int = 624
ENDGAME_QUEEN_VALUE: int = 1141
ENDGAME_KING_VALUE: int = 100000

ENDGAME_PIECE_VALUES: dict[str, int] = {
    "P": ENDGAME_PAWN_VALUE,
    "N": ENDGAME_KNIGHT_VALUE,
    "B": ENDGAME_BISHOP_VALUE,
    "R": ENDGAME_ROOK_VALUE,
    "Q": ENDGAME_QUEEN_VALUE,
    "K": ENDGAME_KING_VALUE,
}

ENDGAME_TROPISM_VALUES: dict[str, int] = {piece: value // 3 for piece, value in ENDGAME_PIECE_VALUES.items()}

ENDGAME_PAWN_TABLE: list[int] = [
       0,    0,    0,    0,    0,    0,    0,    0,
     217,  211,  193,  163,  179,  161,  201,  228,
     115,  122,  104,   82,   68,   65,  100,  102,
      39,   29,   16,    6,   -2,    5,   21,   21,
      16,   11,   -4,   -9,   -9,  -10,    4,   -1,
       5,    9,   -7,    1,    0,   -6,   -1,  -10,
      16,   10,   10,   12,   16,    0,    2,   -9,
       0,    0,    0,    0,    0,    0,    0,    0,
]

ENDGAME_KNIGHT_TABLE: list[int] = [
     -71,  -46,  -16,  -34,  -38,  -33,  -77, -121,
     -30,  -10,  -30,   -2,  -11,  -30,  -29,  -63,
     -29,  -24,   12,   11,   -1,  -11,  -23,  -50,
     -21,    4,   27,   27,   27,   13,   10,  -22,
     -22,   -7,   20,   30,   20,   21,    5,  -22,
     -28,   -4,   -1,   18,   12,   -4,  -24,  -27,
     -51,  -24,  -12,   -6,   -2,  -24,  -28,  -54,
     -35,  -62,  -28,  -18,  -27,  -22,  -61,  -78,
]

ENDGAME_BISHOP_TABLE: list[int] = [
     -17,  -26,  -13,  -10,   -9,  -11,  -21,  -29,
     -10,   -5,    9,  -15,   -4,  -16,   -5,  -17,
       2,  -10,    0,   -1,   -2,    7,    0,    5,
      -4,   11,   15,   11,   17,   12,    4,    2,
      -7,    4,   16,   23,    9,   12,   -4,  -11,
     -15,   -4,   10,   12,   16,    4,   -9,  -18,
     -17,  -22,   -9,   -1,    5,  -11,  -18,  -33,
     -28,  -11,  -28,   -6,  -11,  -20,   -6,  -21,
]

ENDGAME_ROOK_TABLE: list[int] = [
      16,   12,   22,   18,   15,   15,   10,    6,
      13,   16,   16,   13,   -4,    4,   10,    4,
       9,    9,    9,    6,    5,   -4,   -6,   -4,
       5,    4,   16,    1,    2,    1,   -1,    2,
       4,    6,   10,    5,   -6,   -7,  -10,  -13,
      -5,    0,   -6,   -1,   -9,  -15,  -10,  -20,
      -7,   -7,    0,    2,  -11,  -11,  -13,   -4,
     -11,    2,    4,   -1,   -6,  -16,    5,  -24,
]

ENDGAME_QUEEN_TABLE: list[int] = [
     -11,   27,   27,   33,   33,   23,   12,   24,
     -21,   24,   39,   50,   71,   30,   37,    0,
     -24,    7,   11,   60,   57,   43,   23,   11,
       4,   27,   29,   55,   70,   49,   70,   44,
     -22,   34,   23,   57,   38,   41,   48,   28,
     -20,  -33,   18,    7,   11,   21,   12,    6,
     -27,  -28,  -37,  -20,  -20,  -28,  -44,  -39,
     -40,  -34,  -27,  -52,   -6,  -39,  -24,  -50,
]

ENDGAME_KING_TABLE: list[int] = [
     -90,  -43,  -22,  -22,  -13,   18,    5,  -21,
     -15,   21,   17,   21,   21,   46,   28,   13,
      12,   21,   28,   18,   24,   55,   54,   16,
     -10,   27,   29,   33,   32,   40,   32,    4,
     -22,   -5,   26,   29,   33,   28,   11,  -13,
     -23,   -4,   13,   26,   28,   20,    9,  -11,
     -33,  -13,    5,   16,   17,    5,   -6,  -21,
     -65,  -41,  -26,  -13,  -34,  -17,  -29,  -52,
]

ENDGAME_PIECE_SQUARE_TABLES: dict[str, list[int]] = {
    "P": ENDGAME_PAWN_TABLE,
    "N": ENDGAME_KNIGHT_TABLE,
    "B": ENDGAME_BISHOP_TABLE,
    "R": ENDGAME_ROOK_TABLE,
    "Q": ENDGAME_QUEEN_TABLE,
    "K": ENDGAME_KING_TABLE,
}

MOP_UP_SCORE: int = ENDGAME_PAWN_VALUE * 2 # used to encourage kings to be closer to each other if winning an endgame position

# Checkmate scores
CHECKMATE_UPPER: int = ENDGAME_KING_VALUE + 10 * ENDGAME_QUEEN_VALUE
CHECKMATE_LOWER: int = ENDGAME_KING_VALUE - 10 * ENDGAME_QUEEN_VALUE

# Game phase constants to interpolate between midgame and endgame scores
KNIGHT_PHASE: int = 1
BISHOP_PHASE: int = 1
ROOK_PHASE: int = 2
QUEEN_PHASE: int = 4
TOTAL_PHASE: int = 4 * KNIGHT_PHASE + 4 * BISHOP_PHASE + 4 * ROOK_PHASE + 2 * QUEEN_PHASE

# Hashing and PolyGlot opening book constants
HASH_VALUES: list[int] = [
    0x9D39247E33776D41, 0x2AF7398005AAA5C7, 0x44DB015024623547, 0x9C15F73E62A76AE2,
    0x75834465489C0C89, 0x3290AC3A203001BF, 0x0FBBAD1F61042279, 0xE83A908FF2FB60CA,
    0x0D7E765D58755C10, 0x1A083822CEAFE02D, 0x9605D5F0E25EC3B0, 0xD021FF5CD13A2ED5,
    0x40BDF15D4A672E32, 0x011355146FD56395, 0x5DB4832046F3D9E5, 0x239F8B2D7FF719CC,
    0x05D1A1AE85B49AA1, 0x679F848F6E8FC971, 0x7449BBFF801FED0B, 0x7D11CDB1C3B7ADF0,
    0x82C7709E781EB7CC, 0xF3218F1C9510786C, 0x331478F3AF51BBE6, 0x4BB38DE5E7219443,
    0xAA649C6EBCFD50FC, 0x8DBD98A352AFD40B, 0x87D2074B81D79217, 0x19F3C751D3E92AE1,
    0xB4AB30F062B19ABF, 0x7B0500AC42047AC4, 0xC9452CA81A09D85D, 0x24AA6C514DA27500,
    0x4C9F34427501B447, 0x14A68FD73C910841, 0xA71B9B83461CBD93, 0x03488B95B0F1850F,
    0x637B2B34FF93C040, 0x09D1BC9A3DD90A94, 0x3575668334A1DD3B, 0x735E2B97A4C45A23,
    0x18727070F1BD400B, 0x1FCBACD259BF02E7, 0xD310A7C2CE9B6555, 0xBF983FE0FE5D8244,
    0x9F74D14F7454A824, 0x51EBDC4AB9BA3035, 0x5C82C505DB9AB0FA, 0xFCF7FE8A3430B241,
    0x3253A729B9BA3DDE, 0x8C74C368081B3075, 0xB9BC6C87167C33E7, 0x7EF48F2B83024E20,
    0x11D505D4C351BD7F, 0x6568FCA92C76A243, 0x4DE0B0F40F32A7B8, 0x96D693460CC37E5D,
    0x42E240CB63689F2F, 0x6D2BDCDAE2919661, 0x42880B0236E4D951, 0x5F0F4A5898171BB6,
    0x39F890F579F92F88, 0x93C5B5F47356388B, 0x63DC359D8D231B78, 0xEC16CA8AEA98AD76,
    0x5355F900C2A82DC7, 0x07FB9F855A997142, 0x5093417AA8A7ED5E, 0x7BCBC38DA25A7F3C,
    0x19FC8A768CF4B6D4, 0x637A7780DECFC0D9, 0x8249A47AEE0E41F7, 0x79AD695501E7D1E8,
    0x14ACBAF4777D5776, 0xF145B6BECCDEA195, 0xDABF2AC8201752FC, 0x24C3C94DF9C8D3F6,
    0xBB6E2924F03912EA, 0x0CE26C0B95C980D9, 0xA49CD132BFBF7CC4, 0xE99D662AF4243939,
    0x27E6AD7891165C3F, 0x8535F040B9744FF1, 0x54B3F4FA5F40D873, 0x72B12C32127FED2B,
    0xEE954D3C7B411F47, 0x9A85AC909A24EAA1, 0x70AC4CD9F04F21F5, 0xF9B89D3E99A075C2,
    0x87B3E2B2B5C907B1, 0xA366E5B8C54F48B8, 0xAE4A9346CC3F7CF2, 0x1920C04D47267BBD,
    0x87BF02C6B49E2AE9, 0x092237AC237F3859, 0xFF07F64EF8ED14D0, 0x8DE8DCA9F03CC54E,
    0x9C1633264DB49C89, 0xB3F22C3D0B0B38ED, 0x390E5FB44D01144B, 0x5BFEA5B4712768E9,
    0x1E1032911FA78984, 0x9A74ACB964E78CB3, 0x4F80F7A035DAFB04, 0x6304D09A0B3738C4,
    0x2171E64683023A08, 0x5B9B63EB9CEFF80C, 0x506AACF489889342, 0x1881AFC9A3A701D6,
    0x6503080440750644, 0xDFD395339CDBF4A7, 0xEF927DBCF00C20F2, 0x7B32F7D1E03680EC,
    0xB9FD7620E7316243, 0x05A7E8A57DB91B77, 0xB5889C6E15630A75, 0x4A750A09CE9573F7,
    0xCF464CEC899A2F8A, 0xF538639CE705B824, 0x3C79A0FF5580EF7F, 0xEDE6C87F8477609D,
    0x799E81F05BC93F31, 0x86536B8CF3428A8C, 0x97D7374C60087B73, 0xA246637CFF328532,
    0x043FCAE60CC0EBA0, 0x920E449535DD359E, 0x70EB093B15B290CC, 0x73A1921916591CBD,
    0x56436C9FE1A1AA8D, 0xEFAC4B70633B8F81, 0xBB215798D45DF7AF, 0x45F20042F24F1768,
    0x930F80F4E8EB7462, 0xFF6712FFCFD75EA1, 0xAE623FD67468AA70, 0xDD2C5BC84BC8D8FC,
    0x7EED120D54CF2DD9, 0x22FE545401165F1C, 0xC91800E98FB99929, 0x808BD68E6AC10365,
    0xDEC468145B7605F6, 0x1BEDE3A3AEF53302, 0x43539603D6C55602, 0xAA969B5C691CCB7A,
    0xA87832D392EFEE56, 0x65942C7B3C7E11AE, 0xDED2D633CAD004F6, 0x21F08570F420E565,
    0xB415938D7DA94E3C, 0x91B859E59ECB6350, 0x10CFF333E0ED804A, 0x28AED140BE0BB7DD,
    0xC5CC1D89724FA456, 0x5648F680F11A2741, 0x2D255069F0B7DAB3, 0x9BC5A38EF729ABD4,
    0xEF2F054308F6A2BC, 0xAF2042F5CC5C2858, 0x480412BAB7F5BE2A, 0xAEF3AF4A563DFE43,
    0x19AFE59AE451497F, 0x52593803DFF1E840, 0xF4F076E65F2CE6F0, 0x11379625747D5AF3,
    0xBCE5D2248682C115, 0x9DA4243DE836994F, 0x066F70B33FE09017, 0x4DC4DE189B671A1C,
    0x51039AB7712457C3, 0xC07A3F80C31FB4B4, 0xB46EE9C5E64A6E7C, 0xB3819A42ABE61C87,
    0x21A007933A522A20, 0x2DF16F761598AA4F, 0x763C4A1371B368FD, 0xF793C46702E086A0,
    0xD7288E012AEB8D31, 0xDE336A2A4BC1C44B, 0x0BF692B38D079F23, 0x2C604A7A177326B3,
    0x4850E73E03EB6064, 0xCFC447F1E53C8E1B, 0xB05CA3F564268D99, 0x9AE182C8BC9474E8,
    0xA4FC4BD4FC5558CA, 0xE755178D58FC4E76, 0x69B97DB1A4C03DFE, 0xF9B5B7C4ACC67C96,
    0xFC6A82D64B8655FB, 0x9C684CB6C4D24417, 0x8EC97D2917456ED0, 0x6703DF9D2924E97E,
    0xC547F57E42A7444E, 0x78E37644E7CAD29E, 0xFE9A44E9362F05FA, 0x08BD35CC38336615,
    0x9315E5EB3A129ACE, 0x94061B871E04DF75, 0xDF1D9F9D784BA010, 0x3BBA57B68871B59D,
    0xD2B7ADEEDED1F73F, 0xF7A255D83BC373F8, 0xD7F4F2448C0CEB81, 0xD95BE88CD210FFA7,
    0x336F52F8FF4728E7, 0xA74049DAC312AC71, 0xA2F61BB6E437FDB5, 0x4F2A5CB07F6A35B3,
    0x87D380BDA5BF7859, 0x16B9F7E06C453A21, 0x7BA2484C8A0FD54E, 0xF3A678CAD9A2E38C,
    0x39B0BF7DDE437BA2, 0xFCAF55C1BF8A4424, 0x18FCF680573FA594, 0x4C0563B89F495AC3,
    0x40E087931A00930D, 0x8CFFA9412EB642C1, 0x68CA39053261169F, 0x7A1EE967D27579E2,
    0x9D1D60E5076F5B6F, 0x3810E399B6F65BA2, 0x32095B6D4AB5F9B1, 0x35CAB62109DD038A,
    0xA90B24499FCFAFB1, 0x77A225A07CC2C6BD, 0x513E5E634C70E331, 0x4361C0CA3F692F12,
    0xD941ACA44B20A45B, 0x528F7C8602C5807B, 0x52AB92BEB9613989, 0x9D1DFA2EFC557F73,
    0x722FF175F572C348, 0x1D1260A51107FE97, 0x7A249A57EC0C9BA2, 0x04208FE9E8F7F2D6,
    0x5A110C6058B920A0, 0x0CD9A497658A5698, 0x56FD23C8F9715A4C, 0x284C847B9D887AAE,
    0x04FEABFBBDB619CB, 0x742E1E651C60BA83, 0x9A9632E65904AD3C, 0x881B82A13B51B9E2,
    0x506E6744CD974924, 0xB0183DB56FFC6A79, 0x0ED9B915C66ED37E, 0x5E11E86D5873D484,
    0xF678647E3519AC6E, 0x1B85D488D0F20CC5, 0xDAB9FE6525D89021, 0x0D151D86ADB73615,
    0xA865A54EDCC0F019, 0x93C42566AEF98FFB, 0x99E7AFEABE000731, 0x48CBFF086DDF285A,
    0x7F9B6AF1EBF78BAF, 0x58627E1A149BBA21, 0x2CD16E2ABD791E33, 0xD363EFF5F0977996,
    0x0CE2A38C344A6EED, 0x1A804AADB9CFA741, 0x907F30421D78C5DE, 0x501F65EDB3034D07,
    0x37624AE5A48FA6E9, 0x957BAF61700CFF4E, 0x3A6C27934E31188A, 0xD49503536ABCA345,
    0x088E049589C432E0, 0xF943AEE7FEBF21B8, 0x6C3B8E3E336139D3, 0x364F6FFA464EE52E,
    0xD60F6DCEDC314222, 0x56963B0DCA418FC0, 0x16F50EDF91E513AF, 0xEF1955914B609F93,
    0x565601C0364E3228, 0xECB53939887E8175, 0xBAC7A9A18531294B, 0xB344C470397BBA52,
    0x65D34954DAF3CEBD, 0xB4B81B3FA97511E2, 0xB422061193D6F6A7, 0x071582401C38434D,
    0x7A13F18BBEDC4FF5, 0xBC4097B116C524D2, 0x59B97885E2F2EA28, 0x99170A5DC3115544,
    0x6F423357E7C6A9F9, 0x325928EE6E6F8794, 0xD0E4366228B03343, 0x565C31F7DE89EA27,
    0x30F5611484119414, 0xD873DB391292ED4F, 0x7BD94E1D8E17DEBC, 0xC7D9F16864A76E94,
    0x947AE053EE56E63C, 0xC8C93882F9475F5F, 0x3A9BF55BA91F81CA, 0xD9A11FBB3D9808E4,
    0x0FD22063EDC29FCA, 0xB3F256D8ACA0B0B9, 0xB03031A8B4516E84, 0x35DD37D5871448AF,
    0xE9F6082B05542E4E, 0xEBFAFA33D7254B59, 0x9255ABB50D532280, 0xB9AB4CE57F2D34F3,
    0x693501D628297551, 0xC62C58F97DD949BF, 0xCD454F8F19C5126A, 0xBBE83F4ECC2BDECB,
    0xDC842B7E2819E230, 0xBA89142E007503B8, 0xA3BC941D0A5061CB, 0xE9F6760E32CD8021,
    0x09C7E552BC76492F, 0x852F54934DA55CC9, 0x8107FCCF064FCF56, 0x098954D51FFF6580,
    0x23B70EDB1955C4BF, 0xC330DE426430F69D, 0x4715ED43E8A45C0A, 0xA8D7E4DAB780A08D,
    0x0572B974F03CE0BB, 0xB57D2E985E1419C7, 0xE8D9ECBE2CF3D73F, 0x2FE4B17170E59750,
    0x11317BA87905E790, 0x7FBF21EC8A1F45EC, 0x1725CABFCB045B00, 0x964E915CD5E2B207,
    0x3E2B8BCBF016D66D, 0xBE7444E39328A0AC, 0xF85B2B4FBCDE44B7, 0x49353FEA39BA63B1,
    0x1DD01AAFCD53486A, 0x1FCA8A92FD719F85, 0xFC7C95D827357AFA, 0x18A6A990C8B35EBD,
    0xCCCB7005C6B9C28D, 0x3BDBB92C43B17F26, 0xAA70B5B4F89695A2, 0xE94C39A54A98307F,
    0xB7A0B174CFF6F36E, 0xD4DBA84729AF48AD, 0x2E18BC1AD9704A68, 0x2DE0966DAF2F8B1C,
    0xB9C11D5B1E43A07E, 0x64972D68DEE33360, 0x94628D38D0C20584, 0xDBC0D2B6AB90A559,
    0xD2733C4335C6A72F, 0x7E75D99D94A70F4D, 0x6CED1983376FA72B, 0x97FCAACBF030BC24,
    0x7B77497B32503B12, 0x8547EDDFB81CCB94, 0x79999CDFF70902CB, 0xCFFE1939438E9B24,
    0x829626E3892D95D7, 0x92FAE24291F2B3F1, 0x63E22C147B9C3403, 0xC678B6D860284A1C,
    0x5873888850659AE7, 0x0981DCD296A8736D, 0x9F65789A6509A440, 0x9FF38FED72E9052F,
    0xE479EE5B9930578C, 0xE7F28ECD2D49EECD, 0x56C074A581EA17FE, 0x5544F7D774B14AEF,
    0x7B3F0195FC6F290F, 0x12153635B2C0CF57, 0x7F5126DBBA5E0CA7, 0x7A76956C3EAFB413,
    0x3D5774A11D31AB39, 0x8A1B083821F40CB4, 0x7B4A38E32537DF62, 0x950113646D1D6E03,
    0x4DA8979A0041E8A9, 0x3BC36E078F7515D7, 0x5D0A12F27AD310D1, 0x7F9D1A2E1EBE1327,
    0xDA3A361B1C5157B1, 0xDCDD7D20903D0C25, 0x36833336D068F707, 0xCE68341F79893389,
    0xAB9090168DD05F34, 0x43954B3252DC25E5, 0xB438C2B67F98E5E9, 0x10DCD78E3851A492,
    0xDBC27AB5447822BF, 0x9B3CDB65F82CA382, 0xB67B7896167B4C84, 0xBFCED1B0048EAC50,
    0xA9119B60369FFEBD, 0x1FFF7AC80904BF45, 0xAC12FB171817EEE7, 0xAF08DA9177DDA93D,
    0x1B0CAB936E65C744, 0xB559EB1D04E5E932, 0xC37B45B3F8D6F2BA, 0xC3A9DC228CAAC9E9,
    0xF3B8B6675A6507FF, 0x9FC477DE4ED681DA, 0x67378D8ECCEF96CB, 0x6DD856D94D259236,
    0xA319CE15B0B4DB31, 0x073973751F12DD5E, 0x8A8E849EB32781A5, 0xE1925C71285279F5,
    0x74C04BF1790C0EFE, 0x4DDA48153C94938A, 0x9D266D6A1CC0542C, 0x7440FB816508C4FE,
    0x13328503DF48229F, 0xD6BF7BAEE43CAC40, 0x4838D65F6EF6748F, 0x1E152328F3318DEA,
    0x8F8419A348F296BF, 0x72C8834A5957B511, 0xD7A023A73260B45C, 0x94EBC8ABCFB56DAE,
    0x9FC10D0F989993E0, 0xDE68A2355B93CAE6, 0xA44CFE79AE538BBE, 0x9D1D84FCCE371425,
    0x51D2B1AB2DDFB636, 0x2FD7E4B9E72CD38C, 0x65CA5B96B7552210, 0xDD69A0D8AB3B546D,
    0x604D51B25FBF70E2, 0x73AA8A564FB7AC9E, 0x1A8C1E992B941148, 0xAAC40A2703D9BEA0,
    0x764DBEAE7FA4F3A6, 0x1E99B96E70A9BE8B, 0x2C5E9DEB57EF4743, 0x3A938FEE32D29981,
    0x26E6DB8FFDF5ADFE, 0x469356C504EC9F9D, 0xC8763C5B08D1908C, 0x3F6C6AF859D80055,
    0x7F7CC39420A3A545, 0x9BFB227EBDF4C5CE, 0x89039D79D6FC5C5C, 0x8FE88B57305E2AB6,
    0xA09E8C8C35AB96DE, 0xFA7E393983325753, 0xD6B6D0ECC617C699, 0xDFEA21EA9E7557E3,
    0xB67C1FA481680AF8, 0xCA1E3785A9E724E5, 0x1CFC8BED0D681639, 0xD18D8549D140CAEA,
    0x4ED0FE7E9DC91335, 0xE4DBF0634473F5D2, 0x1761F93A44D5AEFE, 0x53898E4C3910DA55,
    0x734DE8181F6EC39A, 0x2680B122BAA28D97, 0x298AF231C85BAFAB, 0x7983EED3740847D5,
    0x66C1A2A1A60CD889, 0x9E17E49642A3E4C1, 0xEDB454E7BADC0805, 0x50B704CAB602C329,
    0x4CC317FB9CDDD023, 0x66B4835D9EAFEA22, 0x219B97E26FFC81BD, 0x261E4E4C0A333A9D,
    0x1FE2CCA76517DB90, 0xD7504DFA8816EDBB, 0xB9571FA04DC089C8, 0x1DDC0325259B27DE,
    0xCF3F4688801EB9AA, 0xF4F5D05C10CAB243, 0x38B6525C21A42B0E, 0x36F60E2BA4FA6800,
    0xEB3593803173E0CE, 0x9C4CD6257C5A3603, 0xAF0C317D32ADAA8A, 0x258E5A80C7204C4B,
    0x8B889D624D44885D, 0xF4D14597E660F855, 0xD4347F66EC8941C3, 0xE699ED85B0DFB40D,
    0x2472F6207C2D0484, 0xC2A1E7B5B459AEB5, 0xAB4F6451CC1D45EC, 0x63767572AE3D6174,
    0xA59E0BD101731A28, 0x116D0016CB948F09, 0x2CF9C8CA052F6E9F, 0x0B090A7560A968E3,
    0xABEEDDB2DDE06FF1, 0x58EFC10B06A2068D, 0xC6E57A78FBD986E0, 0x2EAB8CA63CE802D7,
    0x14A195640116F336, 0x7C0828DD624EC390, 0xD74BBE77E6116AC7, 0x804456AF10F5FB53,
    0xEBE9EA2ADF4321C7, 0x03219A39EE587A30, 0x49787FEF17AF9924, 0xA1E9300CD8520548,
    0x5B45E522E4B1B4EF, 0xB49C3B3995091A36, 0xD4490AD526F14431, 0x12A8F216AF9418C2,
    0x001F837CC7350524, 0x1877B51E57A764D5, 0xA2853B80F17F58EE, 0x993E1DE72D36D310,
    0xB3598080CE64A656, 0x252F59CF0D9F04BB, 0xD23C8E176D113600, 0x1BDA0492E7E4586E,
    0x21E0BD5026C619BF, 0x3B097ADAF088F94E, 0x8D14DEDB30BE846E, 0xF95CFFA23AF5F6F4,
    0x3871700761B3F743, 0xCA672B91E9E4FA16, 0x64C8E531BFF53B55, 0x241260ED4AD1E87D,
    0x106C09B972D2E822, 0x7FBA195410E5CA30, 0x7884D9BC6CB569D8, 0x0647DFEDCD894A29,
    0x63573FF03E224774, 0x4FC8E9560F91B123, 0x1DB956E450275779, 0xB8D91274B9E9D4FB,
    0xA2EBEE47E2FBFCE1, 0xD9F1F30CCD97FB09, 0xEFED53D75FD64E6B, 0x2E6D02C36017F67F,
    0xA9AA4D20DB084E9B, 0xB64BE8D8B25396C1, 0x70CB6AF7C2D5BCF0, 0x98F076A4F7A2322E,
    0xBF84470805E69B5F, 0x94C3251F06F90CF3, 0x3E003E616A6591E9, 0xB925A6CD0421AFF3,
    0x61BDD1307C66E300, 0xBF8D5108E27E0D48, 0x240AB57A8B888B20, 0xFC87614BAF287E07,
    0xEF02CDD06FFDB432, 0xA1082C0466DF6C0A, 0x8215E577001332C8, 0xD39BB9C3A48DB6CF,
    0x2738259634305C14, 0x61CF4F94C97DF93D, 0x1B6BACA2AE4E125B, 0x758F450C88572E0B,
    0x959F587D507A8359, 0xB063E962E045F54D, 0x60E8ED72C0DFF5D1, 0x7B64978555326F9F,
    0xFD080D236DA814BA, 0x8C90FD9B083F4558, 0x106F72FE81E2C590, 0x7976033A39F7D952,
    0xA4EC0132764CA04B, 0x733EA705FAE4FA77, 0xB4D8F77BC3E56167, 0x9E21F4F903B33FD9,
    0x9D765E419FB69F6D, 0xD30C088BA61EA5EF, 0x5D94337FBFAF7F5B, 0x1A4E4822EB4D7A59,
    0x6FFE73E81B637FB3, 0xDDF957BC36D8B9CA, 0x64D0E29EEA8838B3, 0x08DD9BDFD96B9F63,
    0x087E79E5A57D1D13, 0xE328E230E3E2B3FB, 0x1C2559E30F0946BE, 0x720BF5F26F4D2EAA,
    0xB0774D261CC609DB, 0x443F64EC5A371195, 0x4112CF68649A260E, 0xD813F2FAB7F5C5CA,
    0x660D3257380841EE, 0x59AC2C7873F910A3, 0xE846963877671A17, 0x93B633ABFA3469F8,
    0xC0C0F5A60EF4CDCF, 0xCAF21ECD4377B28C, 0x57277707199B8175, 0x506C11B9D90E8B1D,
    0xD83CC2687A19255F, 0x4A29C6465A314CD1, 0xED2DF21216235097, 0xB5635C95FF7296E2,
    0x22AF003AB672E811, 0x52E762596BF68235, 0x9AEBA33AC6ECC6B0, 0x944F6DE09134DFB6,
    0x6C47BEC883A7DE39, 0x6AD047C430A12104, 0xA5B1CFDBA0AB4067, 0x7C45D833AFF07862,
    0x5092EF950A16DA0B, 0x9338E69C052B8E7B, 0x455A4B4CFE30E3F5, 0x6B02E63195AD0CF8,
    0x6B17B224BAD6BF27, 0xD1E0CCD25BB9C169, 0xDE0C89A556B9AE70, 0x50065E535A213CF6,
    0x9C1169FA2777B874, 0x78EDEFD694AF1EED, 0x6DC93D9526A50E68, 0xEE97F453F06791ED,
    0x32AB0EDB696703D3, 0x3A6853C7E70757A7, 0x31865CED6120F37D, 0x67FEF95D92607890,
    0x1F2B1D1F15F6DC9C, 0xB69E38A8965C6B65, 0xAA9119FF184CCCF4, 0xF43C732873F24C13,
    0xFB4A3D794A9A80D2, 0x3550C2321FD6109C, 0x371F77E76BB8417E, 0x6BFA9AAE5EC05779,
    0xCD04F3FF001A4778, 0xE3273522064480CA, 0x9F91508BFFCFC14A, 0x049A7F41061A9E60,
    0xFCB6BE43A9F2FE9B, 0x08DE8A1C7797DA9B, 0x8F9887E6078735A1, 0xB5B4071DBFC73A66,
    0x230E343DFBA08D33, 0x43ED7F5A0FAE657D, 0x3A88A0FBBCB05C63, 0x21874B8B4D2DBC4F,
    0x1BDEA12E35F6A8C9, 0x53C065C6C8E63528, 0xE34A1D250E7A8D6B, 0xD6B04D3B7651DD7E,
    0x5E90277E7CB39E2D, 0x2C046F22062DC67D, 0xB10BB459132D0A26, 0x3FA9DDFB67E2F199,
    0x0E09B88E1914F7AF, 0x10E8B35AF3EEAB37, 0x9EEDECA8E272B933, 0xD4C718BC4AE8AE5F,
    0x81536D601170FC20, 0x91B534F885818A06, 0xEC8177F83F900978, 0x190E714FADA5156E,
    0xB592BF39B0364963, 0x89C350C893AE7DC1, 0xAC042E70F8B383F2, 0xB49B52E587A1EE60,
    0xFB152FE3FF26DA89, 0x3E666E6F69AE2C15, 0x3B544EBE544C19F9, 0xE805A1E290CF2456,
    0x24B33C9D7ED25117, 0xE74733427B72F0C1, 0x0A804D18B7097475, 0x57E3306D881EDB4F,
    0x4AE7D6A36EB5DBCB, 0x2D8D5432157064C8, 0xD1E649DE1E7F268B, 0x8A328A1CEDFE552C,
    0x07A3AEC79624C7DA, 0x84547DDC3E203C94, 0x990A98FD5071D263, 0x1A4FF12616EEFC89,
    0xF6F7FD1431714200, 0x30C05B1BA332F41C, 0x8D2636B81555A786, 0x46C9FEB55D120902,
    0xCCEC0A73B49C9921, 0x4E9D2827355FC492, 0x19EBB029435DCB0F, 0x4659D2B743848A2C,
    0x963EF2C96B33BE31, 0x74F85198B05A2E7D, 0x5A0F544DD2B1FB18, 0x03727073C2E134B1,
    0xC7F6AA2DE59AEA61, 0x352787BAA0D7C22F, 0x9853EAB63B5E0B35, 0xABBDCDD7ED5C0860,
    0xCF05DAF5AC8D77B0, 0x49CAD48CEBF4A71E, 0x7A4C10EC2158C4A6, 0xD9E92AA246BF719E,
    0x13AE978D09FE5557, 0x730499AF921549FF, 0x4E4B705B92903BA4, 0xFF577222C14F0A3A,
    0x55B6344CF97AAFAE, 0xB862225B055B6960, 0xCAC09AFBDDD2CDB4, 0xDAF8E9829FE96B5F,
    0xB5FDFC5D3132C498, 0x310CB380DB6F7503, 0xE87FBB46217A360E, 0x2102AE466EBB1148,
    0xF8549E1A3AA5E00D, 0x07A69AFDCC42261A, 0xC4C118BFE78FEAAE, 0xF9F4892ED96BD438,
    0x1AF3DBE25D8F45DA, 0xF5B4B0B0D2DEEEB4, 0x962ACEEFA82E1C84, 0x046E3ECAAF453CE9,
    0xF05D129681949A4C, 0x964781CE734B3C84, 0x9C2ED44081CE5FBD, 0x522E23F3925E319E,
    0x177E00F9FC32F791, 0x2BC60A63A6F3B3F2, 0x222BBFAE61725606, 0x486289DDCC3D6780,
    0x7DC7785B8EFDFC80, 0x8AF38731C02BA980, 0x1FAB64EA29A2DDF7, 0xE4D9429322CD065A,
    0x9DA058C67844F20C, 0x24C0E332B70019B0, 0x233003B5A6CFE6AD, 0xD586BD01C5C217F6,
    0x5E5637885F29BC2B, 0x7EBA726D8C94094B, 0x0A56A5F0BFE39272, 0xD79476A84EE20D06,
    0x9E4C1269BAA4BF37, 0x17EFEE45B0DEE640, 0x1D95B0A5FCF90BC6, 0x93CBE0B699C2585D,
    0x65FA4F227A2B6D79, 0xD5F9E858292504D5, 0xC2B5A03F71471A6F, 0x59300222B4561E00,
    0xCE2F8642CA0712DC, 0x7CA9723FBB2E8988, 0x2785338347F2BA08, 0xC61BB3A141E50E8C,
    0x150F361DAB9DEC26, 0x9F6A419D382595F4, 0x64A53DC924FE7AC9, 0x142DE49FFF7A7C3D,
    0x0C335248857FA9E7, 0x0A9C32D5EAE45305, 0xE6C42178C4BBB92E, 0x71F1CE2490D20B07,
    0xF1BCC3D275AFE51A, 0xE728E8C83C334074, 0x96FBF83A12884624, 0x81A1549FD6573DA5,
    0x5FA7867CAF35E149, 0x56986E2EF3ED091B, 0x917F1DD5F8886C61, 0xD20D8C88C8FFE65F,
    0x31D71DCE64B2C310, 0xF165B587DF898190, 0xA57E6339DD2CF3A0, 0x1EF6E6DBB1961EC9,
    0x70CC73D90BC26E24, 0xE21A6B35DF0C3AD7, 0x003A93D8B2806962, 0x1C99DED33CB890A1,
    0xCF3145DE0ADD4289, 0xD0E4427A5514FB72, 0x77C621CC9FB3A483, 0x67A34DAC4356550B,
    0xF8D626AAAF278509
]

PIECE_ENCODINGS: dict[str, int] = {
    "p": 0,
    "P": 1,
    "n": 2,
    "N": 3,
    "b": 4,
    "B": 5,
    "r": 6,
    "R": 7,
    "q": 8,
    "Q": 9,
    "k": 10,
    "K": 11
}

DECODED_PROMOTION_PIECES: dict[int, str] = {
    0: "",
    1: "N",
    2: "B",
    3: "R",
    4: "Q",
}

UNICODE_PIECE_SYMBOLS = {
    "R": "♖", "r": "♜",
    "N": "♘", "n": "♞",
    "B": "♗", "b": "♝",
    "Q": "♕", "q": "♛",
    "K": "♔", "k": "♚",
    "P": "♙", "p": "♟",
}

###############
# BOARD LOGIC #
###############

def generate_moves(position: str, castling: list[bool], en_passant: int) -> list[tuple[int, int, str, str]]:
    """Generates all pseudo-legal moves for a given position. Moves are represented as tuples:
    (start_square, end_square, piece_captured, promotion_piece)"""
    move_list: list[tuple[int, int, str, str]] = []
    for start_square in range(len(position)):
        if not position[start_square].isupper():  # piece is not current player's
            continue
        piece_moved: str = position[start_square]
        for direction in PIECE_DIRECTIONS[piece_moved]:
            for end_square in itertools.count(start_square + direction, direction):
                piece_captured: str = position[end_square]
                if piece_captured.isspace() or piece_captured.isupper():  # off the board or ally piece
                    break
                if piece_moved == "P":
                    if direction in [NORTH, NORTH + NORTH] and piece_captured != ".":  # pawn push onto occupied square
                        break
                    if direction == NORTH + NORTH and (start_square < A1 + NORTH or position[start_square + NORTH] != "."):  # double pawn push from invalid rank
                        break
                    if direction in [NORTH + WEST, NORTH + EAST] and piece_captured == "." and end_square + SOUTH != en_passant:  # invalid en passant capture
                        break
                    if A8 <= end_square <= H8:  # pawn promotion
                        for promotion_piece in "QRBN":
                            move_list.append((start_square, end_square, piece_captured, promotion_piece))
                        break
                move_list.append((start_square, end_square, piece_captured, ""))
                if piece_moved in "PNK" or piece_captured.islower():  # non-sliding piece or capture
                    break
                if start_square == A1 and position[end_square + EAST] == "K" and castling[0]:  # the piece is a rook on a1, and the king is on e1 with empty squares in between, and queenside castling is allowed
                    move_list.append((end_square + EAST, end_square + WEST, piece_captured, ""))
                if  start_square == H1 and position[end_square + WEST] == "K" and castling[1]:  # the piece is a rook on h1, and the king is on e1 with empty squares in between, and kingside castling is allowed
                    move_list.append((end_square + WEST, end_square + EAST, piece_captured, ""))
    move_list.sort(key=lambda move: evaluate_move(move, position, en_passant), reverse=True)  # sort moves by basic evaluation
    return move_list


def make_move(move: tuple[int, int, str, str], position: str, castling: list[bool], opponent_castling: list[bool], en_passant: int, king_passant: int) -> tuple[str, list[bool], list[bool], int, int]:
    """Makes a move on the given position."""
    list_position: list[str] = list(position)
    start_square: int = move[0]
    end_square: int = move[1]
    promotion_piece: str = move[3]
    piece_moved: str = list_position[start_square]
    king_passant = 0
    list_position[start_square] = "."
    list_position[end_square] = piece_moved
    if start_square == A1:  # queenside rook moved
        castling[0] = False
    if start_square == H1:  # kingside rook moved
        castling[1] = False
    if end_square == A8:  # opponent queenside rook captured
        opponent_castling[0] = False
    if end_square == H8:  # opponent kingside rook captured
        opponent_castling[1] = False
    if piece_moved == "K":
        king_passant = 0
        castling[0] = False
        castling[1] = False
        if start_square - end_square == 2:  # queenside castling
            king_passant = (start_square + end_square) // 2
            list_position[A1], list_position[king_passant] = list_position[king_passant], list_position[A1]
        if end_square - start_square == 2:  # kingside castling
            king_passant = (start_square + end_square) // 2
            list_position[H1], list_position[king_passant] = list_position[king_passant], list_position[H1]
    elif piece_moved == "P":
        if end_square == en_passant:  # en passant capture
            list_position[end_square + SOUTH] = "."
        if A8 <= end_square <= H8:  # pawn promotion
            list_position[end_square] = promotion_piece
        if end_square - start_square == NORTH + NORTH:  # double pawn push
            en_passant = end_square + SOUTH
        else:
            en_passant = 0
    position = "".join(list_position)
    return position, castling, opponent_castling, en_passant, king_passant


def rotate_position(position: str, castling: list[bool], opponent_castling: list[bool], en_passant: int, king_passant: int) -> tuple[str, list[bool], list[bool], int, int]:
    """Rotates the board 180 degrees and swaps the case of the pieces so that it is from the opponent's point of view.
    Typically called after make_move() since our engine always looks from the current player's point of view."""
    en_passant = 119 - en_passant
    king_passant = 119 - king_passant
    castling, opponent_castling = opponent_castling, castling
    list_position: list[str] = list(position)
    for i in range(60):  # only need to loop through half the board since we're swapping two squares at a time
        if not list_position[i].isspace():
            list_position[119 - i], list_position[i] = list_position[i].swapcase(), list_position[119 - i].swapcase()
    position = "".join(list_position)
    return position, castling, opponent_castling, en_passant, king_passant


def king_in_check(position: str, castling: list[bool], king_passant: int) -> bool:
    """Finds if the opponent's king is in check or if they were in check before castling. Typically called after
    make_move() and rotate_position() to see if the move was legal."""
    king_position: int = position.find("k") if "k" in position else 0  # after rotating the board, our king "becomes the opponent's king" ("k") in that position
    if king_position == 0:
        return True

    # Since we call find_check() after make_move(), we check to see if the move we just made was castling.
    # If it was, we use the king passant square and the original king position to see if they were attacked.
    # If they were, it means that the castling move was illegal.
    castled: bool = False
    original_king_position: int = 0
    if king_passant in [23, 25]:
        original_king_position = 24
        castled = True
    elif king_passant in [24, 26]:
        original_king_position = 25
        castled = True
    move_list: list[tuple[int, int, str, str]] = generate_moves(position, castling[:], 0)
    for move in move_list:
        if move[1] == king_position or move[1] == king_passant:
            return True

        if castled and move[1] == original_king_position:
            return True

    return False


########################
# EVALUATION FUNCTIONS #
########################

def manhattan_distance(square1: int, square2: int) -> int:
    """Calculates the Manhattan distance between two squares."""
    return abs(square1 % 10 - square2 % 10) + abs(square1 // 10 - square2 // 10)


def game_phase(position: str) -> int:
    """Evaluates the current game phase though piece counts."""
    phase: int = TOTAL_PHASE
    phase -= (position.count("N") + position.count("n")) * KNIGHT_PHASE
    phase -= (position.count("B") + position.count("b")) * BISHOP_PHASE
    phase -= (position.count("R") + position.count("r")) * ROOK_PHASE
    phase -= (position.count("Q") + position.count("q")) * QUEEN_PHASE
    return (phase * 256 + (TOTAL_PHASE // 2)) // TOTAL_PHASE


def interpolate(midgame_score: int, endgame_score: int, phase: int) -> int:
    """Uses the game phase to interpolate between the midgame and endgame scores."""
    return ((midgame_score * (256 - phase)) + (endgame_score * phase)) // 256


def evaluate_position(position: str) -> int:
    """Evaluates the given position for the side-to-move using material values, piece square tables, king tropism,
    and mop-up bonus and interpolating between midgame and endgame scores."""
    midgame_score: int = 0
    endgame_score: int = 0
    king_square: int = position.find("K") if "K" in position else 0
    opponent_king_square: int = position.find("k") if "k" in position else 0
    for square, piece in enumerate(position):
        if piece.isupper():  # ally piece
            midgame_score += MIDGAME_PIECE_VALUES[piece] + MIDGAME_PIECE_SQUARE_TABLES[piece][square]
            midgame_score += MIDGAME_TROPISM_VALUES[piece] // manhattan_distance(square, opponent_king_square)
            endgame_score += ENDGAME_PIECE_VALUES[piece] + ENDGAME_PIECE_SQUARE_TABLES[piece][square]
            endgame_score += ENDGAME_TROPISM_VALUES[piece] // manhattan_distance(square, opponent_king_square)
        elif piece.islower():  # opponent piece
            midgame_score -= MIDGAME_PIECE_VALUES[piece.upper()] + MIDGAME_PIECE_SQUARE_TABLES[piece.upper()][(11 - (square // 10)) * 10 + (square % 10)]
            midgame_score -= MIDGAME_TROPISM_VALUES[piece.upper()] // manhattan_distance(square, king_square)
            endgame_score -= ENDGAME_PIECE_VALUES[piece.upper()] + ENDGAME_PIECE_SQUARE_TABLES[piece.upper()][(11 - (square // 10)) * 10 + (square % 10)]
            endgame_score -= ENDGAME_TROPISM_VALUES[piece.upper()] // manhattan_distance(square, king_square)
    mop_up_bonus: int = MOP_UP_SCORE * (14 - manhattan_distance(king_square, opponent_king_square)) // 14
    if endgame_score > 0:
        endgame_score += mop_up_bonus
    elif endgame_score < 0:
        endgame_score -= mop_up_bonus
    return interpolate(midgame_score, endgame_score, game_phase(position))


def evaluate_move(move: tuple[int, int, str, str], position: str, en_passant: int) -> int:
    """Evaluates the given move for the side-to-move by interpolating between midgame and endgame scores."""
    start_square: int = move[0]
    end_square: int = move[1]
    piece_moved: str = position[start_square]
    piece_captured: str = move[2]
    promotion_piece: str = move[3]
    midgame_score: int = MIDGAME_PIECE_SQUARE_TABLES[piece_moved][end_square] - MIDGAME_PIECE_SQUARE_TABLES[piece_moved][start_square]
    endgame_score: int = ENDGAME_PIECE_SQUARE_TABLES[piece_moved][end_square] - ENDGAME_PIECE_SQUARE_TABLES[piece_moved][start_square]
    if piece_captured.islower():  # capture
        midgame_score += MIDGAME_PIECE_VALUES[piece_captured.upper()] + MIDGAME_PIECE_SQUARE_TABLES[piece_captured.upper()][(11 - (end_square // 10)) * 10 + (end_square % 10)]
        endgame_score += ENDGAME_PIECE_VALUES[piece_captured.upper()] + ENDGAME_PIECE_SQUARE_TABLES[piece_captured.upper()][(11 - (end_square // 10)) * 10 + (end_square % 10)]
    if piece_moved == "K" and abs(start_square - end_square) == 2:  # castling
        midgame_score += MIDGAME_PIECE_SQUARE_TABLES["R"][(start_square + end_square) // 2] - MIDGAME_PIECE_SQUARE_TABLES["R"][A1 if end_square < start_square else H1]
        endgame_score += ENDGAME_PIECE_SQUARE_TABLES["R"][(start_square + end_square) // 2] - ENDGAME_PIECE_SQUARE_TABLES["R"][A1 if end_square < start_square else H1]
    if piece_moved == "P":
        if A8 <= end_square <= H8:  # pawn promotion
            midgame_score += MIDGAME_PIECE_SQUARE_TABLES[promotion_piece][end_square] - MIDGAME_PIECE_SQUARE_TABLES["P"][end_square] + MIDGAME_PIECE_VALUES[promotion_piece] - MIDGAME_PIECE_VALUES["P"]
            endgame_score += ENDGAME_PIECE_SQUARE_TABLES[promotion_piece][end_square] - ENDGAME_PIECE_SQUARE_TABLES["P"][end_square] + ENDGAME_PIECE_VALUES[promotion_piece] - ENDGAME_PIECE_VALUES["P"]
        if end_square + SOUTH == en_passant:
            midgame_score += MIDGAME_PIECE_SQUARE_TABLES["P"][(11 - ((end_square + SOUTH) // 10)) * 10 + ((end_square + SOUTH) % 10)]
            endgame_score += ENDGAME_PIECE_SQUARE_TABLES["P"][(11 - ((end_square + SOUTH) // 10)) * 10 + ((end_square + SOUTH) % 10)]
    return interpolate(midgame_score, endgame_score, game_phase(position))


def principal_variation(length: int, position: str, castling: list[bool], opponent_castling: list[bool], en_passant: int, king_passant: int, color: str) -> list[tuple[int, int, str, str]]:
    """Uses the transposition table to find the principal variation for the given position as a list of moves."""
    key: int = zobrist_hash(position, castling[:], opponent_castling[:], en_passant, king_passant, color)
    result: tuple[tuple[int, int, str, str], int, int] | None = TRANSPOSITION_TABLE.get(key)
    if result is None or length <= 0:
        return []

    best_move: tuple[int, int, str, str] = result[0]
    new_position: tuple[str, list[bool], list[bool], int, int] = make_move(best_move, position, castling[:], opponent_castling[:], en_passant, king_passant)
    new_position = rotate_position(*new_position)
    return [best_move] + principal_variation(length - 1, *new_position, "w" if color == "b" else "b")


######################################
# HASHING AND OPENING BOOK FUNCTIONS #
######################################

def load_book(book_name: str) -> list[list[int]]:
    """Loads an opening book and returns it as a list of lists of raw integer data."""
    with open(f"{pathlib.Path(__file__).resolve().parent}/opening-books/{book_name}.bin", "rb") as file:
        file_content: bytes = file.read()
    integer_data: list[int] = list(struct.unpack(">" + ("QHHI" * (len(file_content) // 16)), file_content))
    return [integer_data[i:i + 4] for i in range(0, len(integer_data), 4)]


def zobrist_hash(position: str, castling: list[bool], opponent_castling: list[bool], en_passant: int, king_passant: int, color: str) -> int:
    """Calculates a Zobrist hash for the given position using the PolyGlot book format."""
    if color == "b":
        # Position must be from white's perspective for hashing
        position, castling, opponent_castling, en_passant, king_passant = rotate_position(position, castling[:], opponent_castling[:], en_passant, king_passant)
        turn_hash: int = 0
    else:
        turn_hash: int = HASH_VALUES[780]
    piece_hash: int = 0
    for i, piece in enumerate(position):
        if not piece.isspace() and piece != ".":
            row: int = 9 - (i // 10)
            file: int = (i % 10) - 1
            piece_hash ^= HASH_VALUES[(64 * PIECE_ENCODINGS[piece]) + (8 * row) + file]
    castling_hash: int = 0
    if castling[0]:
        castling_hash ^= HASH_VALUES[768 + 1]
    if castling[1]:
        castling_hash ^= HASH_VALUES[768 + 0]
    if opponent_castling[0]:
        castling_hash ^= HASH_VALUES[768 + 3]
    if opponent_castling[1]:
        castling_hash ^= HASH_VALUES[768 + 2]
    en_passant_hash: int = 0
    if en_passant != 0 and en_passant != 119:
        # Only hash en passant if there is a pawn that can perform the capture (legality of the move is not checked)
        if 41 <= en_passant <= 48:  # white can capture en passant
            if position[en_passant + SOUTH + EAST] == "P":
                en_passant_hash: int = HASH_VALUES[772 + ((en_passant) % 10) - 1]
            elif position[en_passant + SOUTH + WEST] == "P":
                en_passant_hash: int = HASH_VALUES[772 + ((en_passant) % 10) - 1]
        elif 71 <= en_passant <= 78:  # black can capture en passant
            if position[en_passant + NORTH + EAST] == "p":
                en_passant_hash: int = HASH_VALUES[772 + ((en_passant) % 10) - 1]
            elif position[en_passant + NORTH + WEST] == "p":
                en_passant_hash: int = HASH_VALUES[772 + ((en_passant) % 10) - 1]
    return piece_hash ^ castling_hash ^ en_passant_hash ^ turn_hash


def all_entries(opening_book: list[list[int]], position: str, castling: list[bool], opponent_castling: list[bool], en_passant: int, king_passant: int, color: str) -> list[tuple[tuple[int, int, str, str], int]]:
    """Returns all entries in the PolyGlot opening book for the given position."""
    key: int = zobrist_hash(position, castling[:], opponent_castling[:], en_passant, king_passant, color)
    entries: list[tuple[tuple[int, int, str, str], int]] = []
    for entry_key, raw_move, weight, _ in opening_book:
        if entry_key == key:
            endian_start_square: int = (raw_move >> 6) & 0x3f
            endian_end_square: int = raw_move & 0x3f
            encoded_promotion_piece: int = (raw_move >> 12) & 0x7
            start_square: int = 10 * (9 - (endian_start_square // 8)) + (endian_start_square % 8) + 1  # convert to our 10x12 representation
            end_square: int = 10 * (9 - (endian_end_square // 8)) + (endian_end_square % 8) + 1
            promotion_piece: str = DECODED_PROMOTION_PIECES[encoded_promotion_piece]
            if color == "b":  # flip move if from black's perspective
                start_square = 119 - start_square
                end_square = 119 - end_square
            if start_square == 95 or start_square == 94:  # adjust castling since PolyGlot represents it as e1h1 or e1a1 (instead of e1g1 or e1c1)
                if end_square == H1:
                    end_square = start_square + 2
                elif end_square == A1:
                    end_square = start_square - 2
            move: tuple[int, int, str, str] = (start_square, end_square, position[end_square], promotion_piece)
            entries.append((move, weight))
    return entries


def book_entries(position: str, castling: list[bool], opponent_castling: list[bool], en_passant: int, king_passant: int, color: str) -> tuple[tuple[int, int, str, str], tuple[int, int, str, str]]:
    """Returns the maximum entry and a random entry by weight from the PolyGlot opening book for the given position."""

    total_entries: list[tuple[tuple[int, int, str, str], int]] = []

    for book in OPENING_BOOKS:
        entries: list[tuple[tuple[int, int, str, str], int]] = all_entries(book, position, castling[:], opponent_castling[:], en_passant, king_passant, color)
        for new_entry in entries:
            found: bool = False
            for i, entry in enumerate(total_entries):
                if entry[0] == new_entry[0]:
                    total_entries[i] = (entry[0], entry[1] + new_entry[1]) # combine the weights of all opening books
                    found = True
                    break
            if not found:
                total_entries.append(new_entry) # add new entries to the list if not already present

    if len(total_entries) == 0:
        return (0, 0, "", ""), (0, 0, "", "")

    max_entry: tuple[int, int, str, str] = max(total_entries, key=lambda pair: (pair[1], evaluate_move(pair[0], position, en_passant)))[0]
    weighted_entry: tuple[int, int, str, str] = (0, 0, "", "")
    weight_sum: int = sum([entry[1] for entry in total_entries])
    target: int = random.randint(0, weight_sum)
    random.shuffle(total_entries)
    current_sum: int = 0
    for entry in total_entries:
        current_sum += entry[1]
        if current_sum >= target:
            weighted_entry = entry[0]
            break
    return max_entry, weighted_entry


################
# SEARCH LOGIC #
################

def quiesce(alpha: int, beta: int, position: str, castling: list[bool], opponent_castling: list[bool], en_passant: int, king_passant: int) -> int:
    """Performs a fail-hard quiescent search (searches captures only until a quiet position is reached) with delta
    pruning."""
    global nodes, start_time, time_limit, timeout
    if time.time() - start_time > time_limit:
        timeout = True
        return 0

    nodes += 1
    stand_pat: int = evaluate_position(position)
    if stand_pat >= beta:
        return stand_pat

    if alpha < stand_pat:
        alpha = stand_pat
    move_list: list[tuple[int, int, str, str]] = generate_moves(position, castling[:], en_passant)
    for move in move_list:
        if not move[2].islower():  # not a capture
            continue
        new_position: tuple[str, list[bool], list[bool], int, int] = make_move(move, position, castling[:], opponent_castling[:], en_passant, king_passant)
        new_position = rotate_position(*new_position)
        if king_in_check(new_position[0], castling[:], new_position[4]): # if the move results in our king being in check (illegal move)
            continue
        delta: int = 200  # delta safety margin to account for potential positional compensation
        if stand_pat + ENDGAME_PIECE_VALUES[move[2].upper()] + (ENDGAME_PIECE_VALUES[move[3]] if move[3].isupper() else 0) + delta < alpha:  # delta pruning
            continue
        score = -quiesce(-beta, -alpha, *new_position)
        if timeout:
            return 0

        if score >= beta:
            return beta # fail-hard beta cutoff

        if score > alpha:
            alpha = score
    return alpha


def nega_max(depth: int, alpha: int, beta: int, position: str, castling: list[bool], opponent_castling: list[bool], en_passant: int, king_passant: int, color: str) -> tuple[int, tuple[int, int, str, str]]:
    """Performs a fail-hard negamax search with alpha-beta pruning on the given position, returning the best score and
    move found after the search."""
    global max_depth, nodes, start_time, time_limit, timeout
    if time.time() - start_time > time_limit:
        timeout = True
        return 0, (0, 0, "", "")

    if depth == 0:
        return quiesce(alpha, beta, position, castling[:], opponent_castling[:], en_passant, king_passant), (0, 0, "", "")

    key: int = zobrist_hash(position, castling[:], opponent_castling[:], en_passant, king_passant, color)
    table_info: tuple[tuple[int, int, str, str], int, int] | None = TRANSPOSITION_TABLE.get(key)
    if table_info is None:
        table_info = ((0, 0, "", ""), -1, 0)
    if table_info[1] >= depth or table_info[2] >= CHECKMATE_LOWER:  # move is from higher depth or position is checkmate
        return table_info[2], table_info[0]

    nodes += 1
    legal_moves: list[tuple[int, int, str, str]] = []  # keep track of legal moves for checkmate and stalemate detection
    move_list: list[tuple[int, int, str, str]] = generate_moves(position, castling[:], en_passant)
    for i in range(len(move_list)):  # basic PV move ordering: transposition table move from lower depth goes first
        if move_list[i] == table_info[0]:
            move_list.insert(0, move_list.pop(i))
            break
    best_move: tuple[int, int, str, str] = (0, 0, "", "")
    for move in move_list:
        new_position: tuple[str, list[bool], list[bool], int, int] = make_move(move, position, castling[:], opponent_castling[:], en_passant, king_passant)
        new_position = rotate_position(*new_position)
        if king_in_check(new_position[0], castling[:], new_position[4]):  # if the move results in our king being in check (illegal move)
            continue
        legal_moves.append(move)
        score: int = -nega_max(depth - 1, -beta, -alpha, *new_position, "w" if color == "b" else "b")[0]
        if timeout:
            return 0, (0, 0, "", "")

        if score >= beta:
            return beta, best_move  # fail-hard beta cutoff

        if score > alpha:
            alpha = score
            best_move = move
    if len(legal_moves) == 0:  # if there are no legal moves, it's either checkmate or stalemate.
        new_position = rotate_position(position, castling[:], opponent_castling[:], en_passant, king_passant)
        if king_in_check(new_position[0], castling[:], 0):
            return -CHECKMATE_LOWER + max_depth - depth, (0, 0, "", "")

        else:
            return 0, (0, 0, "", "")

    if best_move != (0, 0, "", ""):
        key: int = zobrist_hash(position, castling[:], opponent_castling[:], en_passant, king_passant, color)
        TRANSPOSITION_TABLE[key] = (best_move, depth, alpha)
    return alpha, best_move


def iteratively_deepen(depth: int, position: str, castling: list[bool], opponent_castling: list[bool], en_passant: int, king_passant: int, color: str) -> tuple[int, int, str, str]:
    """Wraps the negamax search function in an iterative deepening loop, utilizing the transposition table and PV move
    ordering to improve search efficiency."""
    global max_depth, nodes, start_time, timeout
    weighted_entry: tuple[int, int, str, str]
    _, weighted_entry = book_entries(position, castling[:], opponent_castling[:], en_passant, king_passant, color)
    if weighted_entry != (0, 0, "", ""):
        send_response(f"info string weighted bookmove")
        return weighted_entry

    # max_entry: tuple[int, int, str, str]
    # max_entry, _ = book_entries(position, castling[:], opponent_castling[:], en_passant, king_passant, color)
    # if max_entry != (0, 0, "", ""):
    #     send_response(f"info string max bookmove")
    #     return max_entry

    score: int = 0
    best_move: tuple[int, int, str, str] = (0, 0, "", "")
    previous_best_move: tuple[int, int, str, str] = (0, 0, "", "")
    start_time = time.time()
    timeout = False
    for max_depth in range(1, depth + 1):
        nodes = 0
        score, best_move = nega_max(max_depth, -CHECKMATE_UPPER, CHECKMATE_UPPER, position, castling[:], opponent_castling[:], en_passant, king_passant, color)
        if timeout:
            timeout = False
            best_move = previous_best_move
            break
        pv_string: str = ""
        for i, move in enumerate(principal_variation(max_depth, position, castling[:], opponent_castling[:], en_passant, king_passant, color)):
            if i % 2 == 0:
                pv_string += algebraic_notation(move, color) + " "
            else:
                pv_string += algebraic_notation(move, ("b" if color == "w" else "w")) + " "
        send_response(f"info depth {max_depth} score cp {score * (-1 if color == 'b' else 1)} nodes {nodes} time {int(round(time.time() - start_time, 3) * 1000)} pv {pv_string.rstrip()}")
        if best_move == (0, 0, "", ""):
            break
        previous_best_move = best_move
    return best_move


#####################
# UTILITY FUNCTIONS #
#####################

def parse_coordinates(coordinate: str) -> int:
    """Converts a coordinate string (e.g. "a1") to an integer matching an index in the board representation."""
    file: int = ord(coordinate[0]) - ord("a")
    rank: int = int(coordinate[1]) - 1
    return A1 + file - 10 * rank


def render_coordinates(index: int) -> str:
    """Converts an index in the board representation to a coordinate string (e.g. "a1")."""
    rank: int = (index - A1) // 10
    file: int = (index - A1) % 10
    return chr(ord("a") + file) + str(1 - rank)

def algebraic_notation(move: tuple[int, int, str, str], color: str) -> str:
    """Converts a move from the internal representation to long algebraic notation"""
    start_square: int = move[0]
    end_square: int = move[1]
    promotion_piece: str = move[3]
    if color == "b":
        start_square = 119 - start_square
        end_square = 119 - end_square
    if move == (0, 0, "", ""):
        return "(none)"

    return render_coordinates(start_square) + render_coordinates(end_square) + promotion_piece.lower()


def load_fen(fen: str) -> tuple[str, list[bool], list[bool], int, int, str]:
    """Configures the board according to the given FEN string and returns the position information."""
    list_position: list[str] = [" "] * 120
    fields: list[str] = fen.split(" ")
    rows: list[str] = fields[0].split("/")
    for row in range(8):
        index: int = A8 + (10 * row)
        for piece in rows[row]:
            if piece in "PNBRQKpnbrqk":
                list_position[index] = piece
                index += 1
            elif piece in "12345678":
                for _ in range(int(piece)):
                    list_position[index] = "."
                    index += 1
    for new_line_index in [9, 19, 29, 39, 49, 59, 69, 79, 89, 99, 109, 119]:
        list_position[new_line_index] = "\n"
    castling_rights = fields[2]
    position = "".join(list_position)
    castling: list[bool] = [True if "Q" in castling_rights else False, True if "K" in castling_rights else False]
    opponent_castling: list[bool] = [True if "q" in castling_rights else False, True if "k" in castling_rights else False]
    en_passant: int = parse_coordinates(fields[3]) if fields[3] != "-" else 0
    king_passant: int = 0
    color = fields[1]
    if color == "b":
        position, castling, opponent_castling, en_passant, king_passant = rotate_position(position, castling[:], opponent_castling[:], en_passant, king_passant)
    return position, castling, opponent_castling, en_passant, king_passant, color


def generate_fen(position: str, castling: list[bool], opponent_castling: list[bool], en_passant: int, king_passant: int, color: str) -> str:
    """Returns a FEN string representing the given position."""
    if color == "b":
        position, castling, opponent_castling, en_passant, king_passant = rotate_position(position, castling[:], opponent_castling[:], en_passant, king_passant)
    fen: str = ""
    for rank in range(8):
        empty_squares: int = 0
        for file in range(8):
            piece: str = position[(10 * (rank + 2)) + file + 1]
            if piece == ".":
                empty_squares += 1
            else:
                if empty_squares > 0:
                    fen += str(empty_squares)
                    empty_squares = 0
                fen += piece
        if empty_squares > 0:
            fen += str(empty_squares)
        if rank < 7:
            fen += "/"
    fen += " w" if color == "w" else " b"
    if castling[0] or castling[1] or opponent_castling[0] or opponent_castling[1]:
        fen += " "
        fen += "K" if castling[1] else ""
        fen += "Q" if castling[0] else ""
        fen += "k" if opponent_castling[1] else ""
        fen += "q" if opponent_castling[0] else ""
    else:
        fen += " -"
    fen += " -" if en_passant == 0 or en_passant == 119 else f" {render_coordinates(en_passant)}"
    fen += " 0 1"  # halfmove clock and fullmove number are not used
    return fen


def display_board(position: str, castling: list[bool], opponent_castling: list[bool], en_passant: int, king_passant: int, color: str, unicode: bool = False) -> list[str]:
    """Converts the position into a list of strings in which each string represents a row in an text display of the
    board."""
    if color == "b":
        position, castling, opponent_castling, en_passant, king_passant = rotate_position(position, castling[:], opponent_castling[:], en_passant, king_passant)
    board: list[str] = []
    for rank in range(8):
        board.append("+---+---+---+---+---+---+---+---+")
        row: str = "|"
        for file in range(8):
            piece: str = position[(10 * (rank + 2)) + file + 1]
            row += (f" {(UNICODE_PIECE_SYMBOLS[piece] if unicode else piece) if piece != '.' else ' '} |")
        row += (f" {str(8 - rank)}")
        board.append("".join(row))
    board.append("+---+---+---+---+---+---+---+---+")
    board.append("  a   b   c   d   e   f   g   h")
    return board


################
# UCI PROTOCOL #
################

def send_response(response: str) -> None:
    """Sends the given response to the stdout, flushing the buffer."""
    sys.stdout.write(response + "\n")
    sys.stdout.flush()


def main() -> None:
    """The main UCI loop responsible for parsing commands and sending responses."""
    global max_depth, nodes, start_time, time_limit, timeout, OPENING_BOOKS
    position: str = ""
    castling: list[bool] = []
    opponent_castling: list[bool] = []
    en_passant: int = 120
    king_passant: int = 120
    color: str = ""

    initialized: bool = False

    while True:
        command: str = sys.stdin.readline().strip()
        tokens: list[str] = command.split()
        if len(tokens) == 0:
            continue
        if tokens[0] == "uci":
            send_response(f"id name {NAME} {VERSION}")
            send_response(f"id author {AUTHOR}")
            send_response("uciok")
        elif tokens[0] == "quit":
            sys.exit()
        elif tokens[0] == "isready":
            if not initialized:
                initialized = True
                # Pad the midgame and endgame tables with zeros to make them 10x12
                for piece in "PNBRQK":
                    blank_row: list[int] = [0] * 10
                    new_midgame_table: list[int] = blank_row + blank_row
                    new_endgame_table: list[int] = blank_row + blank_row
                    for row in range(0, 64, 8):
                        new_midgame_table += [0] + MIDGAME_PIECE_SQUARE_TABLES[piece][row:row + 8] + [0]
                        new_endgame_table += [0] + ENDGAME_PIECE_SQUARE_TABLES[piece][row:row + 8] + [0]
                    MIDGAME_PIECE_SQUARE_TABLES[piece] = new_midgame_table + blank_row + blank_row
                    ENDGAME_PIECE_SQUARE_TABLES[piece] = new_endgame_table + blank_row + blank_row
                # Load opening book data
                OPENING_BOOKS = [load_book("main" + str(num)) for num in range(1, 8)]  # possible to load each book individually
                # Global variable initialization
                max_depth = 0
                nodes = 0
                start_time = 0
                time_limit = 0
                timeout = False
            send_response("readyok")
        elif not initialized:
            continue  # ignore most commands until the engine is properly initialized with "isready"
        elif tokens[0] == "position":
            if len(tokens) >= 2 and tokens[1] == "startpos":
                position = INITIAL_POSITION
                castling = INITIAL_CASTLING[:]
                opponent_castling = INITIAL_OPPONENT_CASTLING[:]
                en_passant = INITIAL_EN_PASSANT
                king_passant = INITIAL_KING_PASSANT
                color = INITIAL_COLOR
            elif len(tokens) >= 8 and tokens[1] == "fen":
                fen: str = " ".join(tokens[2:8])
                position, castling, opponent_castling, en_passant, king_passant, color = load_fen(fen)
            if "moves" in tokens:
                moves_index: int = tokens.index("moves") + 1
                if moves_index < 3:
                    continue
                moves: list[str] = tokens[moves_index:]
                ply: int = 0
                for ply, move in enumerate(moves):  # note that we don't actually check if the moves are legal
                    if move[1].isdigit() and move[3].isdigit():  # make sure the move is in long algebraic notation
                        start_square: int = parse_coordinates(move[:2])
                        end_square: int = parse_coordinates(move[2:4])
                        promotion_piece: str = move[4:].upper()
                        if color == "b":  # if black to move, flip the coordinates
                            start_square = 119 - start_square
                            end_square = 119 - end_square
                        if ply % 2 == 1:  # opponent's move so we flip the coordinates, then rotate the board before and after making the move
                            start_square = 119 - start_square
                            end_square = 119 - end_square
                            position, castling, opponent_castling, en_passant, king_passant = rotate_position(position, castling[:], opponent_castling[:], en_passant, king_passant)
                            position, castling, opponent_castling, en_passant, king_passant = make_move((start_square, end_square, ".", promotion_piece), position, castling[:], opponent_castling[:], en_passant, king_passant)
                            position, castling, opponent_castling, en_passant, king_passant = rotate_position(position, castling[:], opponent_castling[:], en_passant, king_passant)
                        else:  # our move so we just make it
                            position, castling, opponent_castling, en_passant, king_passant = make_move((start_square, end_square, ".", promotion_piece), position, castling[:], opponent_castling[:], en_passant, king_passant)
                if ply % 2 == 0:  # rotate the board after the last move was made and switch the color
                    position, castling, opponent_castling, en_passant, king_passant = rotate_position(position, castling[:], opponent_castling[:], en_passant, king_passant)
                    if color == "w":
                        color = "b"
                    elif color == "b":
                        color = "w"
            king_passant = 0
        elif tokens[0] == "go":
            if len(position) != 120 or len(castling) != 2 or len(opponent_castling) != 2 or not 0 <= en_passant <= 119 or not 0 <= king_passant <= 119 or color not in ("w", "b"):  # invalid position
                continue
            depth: int = 5
            time_limit = 10  # all times are in seconds
            if "movetime" in tokens:
                movetime_index: int = tokens.index("movetime") + 1
                if tokens[movetime_index].isdigit():
                    time_limit  = int(tokens[movetime_index]) / 1000
            if "depth" in tokens:
                depth_index: int = tokens.index("depth") + 1
                if tokens[depth_index].isdigit():
                    depth = int(tokens[depth_index])
            if "wtime" in tokens or "btime" in tokens or "winc" in tokens or "binc" in tokens:
                white_time: float = 400  # default values in case not all time controls are specified
                black_time: float = 400  # these values equate to about 10 seconds of move time
                white_increment: float = 0
                black_increment: float = 0
                if "wtime" in tokens:
                    white_time_index: int = tokens.index("wtime") + 1
                    if tokens[white_time_index].isdigit():
                        white_time = int(tokens[white_time_index]) / 1000
                if "btime" in tokens:
                    black_time_index: int = tokens.index("btime") + 1
                    if tokens[black_time_index].isdigit():
                        black_time = int(tokens[black_time_index]) / 1000
                if "winc" in tokens:
                    white_increment_index: int = tokens.index("winc") + 1
                    if tokens[white_increment_index].isdigit():
                        white_increment = int(tokens[white_increment_index]) / 1000
                if "binc" in tokens:
                    black_increment_index: int = tokens.index("binc") + 1
                    if tokens[black_increment_index].isdigit():
                        black_increment = int(tokens[black_increment_index]) / 1000
                if color == 'b':
                    white_time, black_time = black_time, white_time
                    white_increment, black_increment = black_increment, white_increment
                if white_time <= 60:
                    time_limit = 1
                else:
                    time_limit = white_time / 40 + white_increment
            # Technically, we have to be able to recieve the `stop` command at any time but we'd need concurrency to do so
            best_move: tuple[int, int, str, str] = iteratively_deepen(depth, position, castling[:], opponent_castling[:], en_passant, king_passant, color)
            send_response(f"bestmove {algebraic_notation(best_move, color)}")
        elif tokens[0] == "eval":
            score: float = evaluate_position(position) / 100
            if color == "b":
                score *= -1
            send_response(f"static eval: {'+' if str(score)[0] != '-' else ''}{score}")
        elif tokens[0] == "board":
            if len(tokens) >= 2 and tokens[1] == "unicode":
                board = display_board(position, castling[:], opponent_castling[:], en_passant, king_passant, color, unicode=True)
            else:
                board = display_board(position, castling[:], opponent_castling[:], en_passant, king_passant, color)
            for row in board:
                send_response(row)
            send_response(f"FEN: {generate_fen(position, castling[:], opponent_castling[:], en_passant, king_passant, color)}")
            send_response(f"HASH: {hex(zobrist_hash(position, castling[:], opponent_castling[:], en_passant, king_passant, color)).upper()}")
        elif tokens[0] == "flip":
            position, castling, opponent_castling, en_passant, king_passant = rotate_position(position, castling[:], opponent_castling[:], en_passant, king_passant)
            if color == "w":
                color = "b"
            elif color == "b":
                color = "w"


if __name__ == "__main__":
    main()
