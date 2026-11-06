#!/usr/bin/env python3
"""Source of the shared pixel sprite library.

Each sprite is a list of equal-length rows. One character is one pixel.
'.' is transparent. Other characters are palette keys (see PALETTE).

Run:  python3 tools/sprites_src.py            -> writes engine/library/sprites.json
      python3 tools/sprites_src.py --sheet F  -> also writes a PNG contact sheet
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# A warm "paper" take on the PICO-8 palette.
PALETTE = {
    "k": "#241f2e",  # ink
    "e": "#3b3046",  # deep shadow
    "n": "#1d2b53",  # navy
    "u": "#7e2553",  # plum
    "t": "#008751",  # green
    "m": "#ab5236",  # brown
    "s": "#6b3e26",  # dark wood
    "d": "#5f574f",  # dark grey
    "g": "#c2c3c7",  # grey
    "w": "#fff1e8",  # paper white
    "r": "#ff004d",  # red
    "o": "#ffa300",  # orange
    "y": "#ffec27",  # yellow
    "l": "#00e436",  # lime
    "b": "#29adff",  # blue
    "v": "#83769c",  # lavender
    "p": "#ff77a8",  # pink
    "c": "#ffccaa",  # peach
    "a": "#e8d5b0",  # card / cardboard light
    "z": "#c9a66b",  # cardboard dark
}

S = {}

# --- Characters -----------------------------------------------------------

S["robot"] = [
    ".......oo.......",
    ".......kk.......",
    "...kkkkkkkkkk...",
    "..kggggggggggk..",
    "..kgnnnnnnnngk..",
    "..kgnbbnnbbngk..",
    "..kgnbbnnbbngk..",
    "..kgnnnnnnnngk..",
    "..kggggggggggk..",
    "...kkkkkkkkkk...",
    "....kkkkkkkk....",
    "..kkbbbbbbbbkk..",
    ".kgkbbwwwwbbkgk.",
    ".kgkbbbbbbbbkgk.",
    "..k.kkkkkkkk.k..",
    "....kk....kk....",
]

S["robot_wave"] = [
    ".......oo.......",
    ".......kk.....k.",
    "...kkkkkkkkkkkgk",
    "..kggggggggggkgk",
    "..kgnnnnnnnngkgk",
    "..kgnbbnnbbngkgk",
    "..kgnbbnnbbngkk.",
    "..kgnnnnnnnngk..",
    "..kggggggggggk..",
    "...kkkkkkkkkk...",
    "....kkkkkkkk....",
    "..kkbbbbbbbbkk..",
    ".kgkbbwwwwbbk...",
    ".kgkbbbbbbbbk...",
    "..k.kkkkkkkk....",
    "....kk....kk....",
]

S["robot_happy"] = [
    ".......yy.......",
    ".......kk.......",
    "...kkkkkkkkkk...",
    "..kggggggggggk..",
    "..kgnnnnnnnngk..",
    "..kgnbnnnnbngk..",
    "..kgbnbnnbnbgk..",
    "..kgnnnnnnnngk..",
    "..kggggggggggk..",
    "...kkkkkkkkkk...",
    "....kkkkkkkk....",
    "..kkbbbbbbbbkk..",
    ".kgkbbwwwwbbkgk.",
    ".kgkbbbbbbbbkgk.",
    "..k.kkkkkkkk.k..",
    "....kk....kk....",
]

S["robot_sleep"] = [
    "................",
    ".......kk.......",
    "...kkkkkkkkkk...",
    "..kggggggggggk..",
    "..kgnnnnnnnngk..",
    "..kgnnnnnnnngk..",
    "..kgnbbnnbbngk..",
    "..kgnnnnnnnngk..",
    "..kggggggggggk..",
    "...kkkkkkkkkk...",
    "....kkkkkkkk....",
    "..kkbbbbbbbbkk..",
    ".kgkbbwwwwbbkgk.",
    ".kgkbbbbbbbbkgk.",
    "..k.kkkkkkkk.k..",
    "....kk....kk....",
]

S["robin"] = [
    "....kkkk....",
    "...kmmmmk...",
    "..kmmwkmmk..",
    "..kmmmmmmkoo",
    ".kmrrrmmmkk.",
    "kmrrrrrmmmk.",
    "kmrrrrrmmmmk",
    "kmrrrrmmmmmk",
    ".kmrrmmmmkk.",
    "..kkmmmkk...",
    "....o..o....",
    "...oo.oo....",
]

S["owl"] = [
    ".kk......kk.",
    ".kmk....kmk.",
    ".kmmkkkkmmk.",
    "kmmmmmmmmmmk",
    "kmwwmmmmwwmk",
    "kwykwmmwykwk",
    "kmwwmoomwwmk",
    "kmmmmoommmmk",
    "kmmcccccmmmk",
    "kmcmcmcmcmmk",
    "kmmcccccmmmk",
    ".kmcmcmcmmk.",
    "..kkmmmmkk..",
    "...ko..ok...",
]

S["person"] = [
    "....kkkk....",
    "...kmmmmk...",
    "..kmccccmk..",
    "..kcckcckk..",
    "..kccccck...",
    "...kcrrck...",
    "....kkkk....",
    "..kkttttkk..",
    ".kcktttttkc.",
    ".kcktttttkck",
    "..kktttttk..",
    "...knnnnk...",
    "...knk.nk...",
    "...knk.nk...",
    "..kkk..kkk..",
]

# --- Props: knowledge and work -------------------------------------------

S["shelf"] = [
    "kkkkkkkkkkkkkkkkkkkkkkkk",
    "kssssssssssssssssssssssk",
    "ks....................sk",
    "ks....................sk",
    "ks....................sk",
    "ks....................sk",
    "kssssssssssssssssssssssk",
    "ks....................sk",
    "ks....................sk",
    "ks....................sk",
    "ks....................sk",
    "kssssssssssssssssssssssk",
    "ks....................sk",
    "ks....................sk",
    "kssssssssssssssssssssssk",
    "kk....................kk",
]

S["shelf_full"] = [
    "kkkkkkkkkkkkkkkkkkkkkkkk",
    "kssssssssssssssssssssssk",
    "ksrrbbyttooprrnnbbllvvsk",
    "ksrrbbyttooprrnnbbllvvsk",
    "ksrwbbyttwoprwnnbwllvvsk",
    "ksrrbbyttooprrnnbbllvvsk",
    "kssssssssssssssssssssssk",
    "ksttoorrbbvv.yyppnnrrtsk",
    "ksttoorrbbvvyyyppnnrrtsk",
    "kswtowrrbwvvyyypwnnrwtsk",
    "ksttoorrbbvvyyyppnnrrtsk",
    "kssssssssssssssssssssssk",
    "ksbbnnyyrrllttbbooppvvsk",
    "ksbbnnyyrrllttbbooppvvsk",
    "kssssssssssssssssssssssk",
    "kk....................kk",
]

S["book_stack"] = [
    "..kkkkkkkk..",
    "..krrrrrrk..",
    "..kwwwwwwk..",
    ".kkkkkkkkkk.",
    ".kbbbbbbbbk.",
    ".kwwwwwwwwk.",
    "kkkkkkkkkkk.",
    "kyyyyyyyyyk.",
    "kwwwwwwwwwk.",
    "kkkkkkkkkkkk",
    "kttttttttttk",
    "kkkkkkkkkkkk",
]

S["book_open"] = [
    ".kkkkk..kkkkk.",
    "kwwwwwkkwwwwwk",
    "kwkkkwkkwkkkwk",
    "kwwwwwkkwwwwwk",
    "kwkkwwkkwkkwwk",
    "kwwwwwkkwwwwwk",
    "kwkkkwkkwkkkwk",
    "kwwwwwkkwwwwwk",
    ".kkkkkkkkkkkk.",
]

S["paper"] = [
    "kkkkkkk.",
    "kwwwwwkk",
    "kwkkkwwk",
    "kwwwwwwk",
    "kwkkkkwk",
    "kwwwwwwk",
    "kwkkkwwk",
    "kwwwwwwk",
    "kkkkkkkk",
]

S["sticky_y"] = [
    "kkkkkkk",
    "kyyyyyk",
    "kykkyyk",
    "kyyyyyk",
    "kykkkyk",
    "kyyyyok",
    "kkkkkkk",
]
S["sticky_p"] = [row.replace("y", "p").replace("o", "u") for row in S["sticky_y"]]
S["sticky_b"] = [row.replace("y", "b").replace("o", "n") for row in S["sticky_y"]]
S["sticky_l"] = [row.replace("y", "l").replace("o", "t") for row in S["sticky_y"]]

S["board"] = [
    "kkkkkkkkkkkkkkkkkkkkkkkkkkkk",
    "kmmmmmmmmmmmmmmmmmmmmmmmmmmk",
    "kmzzzzzzzzzzzzzzzzzzzzzzzzmk",
    "kmzzzzzzzzzzzzzzzzzzzzzzzzmk",
    "kmzzzzzzzzzzzzzzzzzzzzzzzzmk",
    "kmzzzzzzzzzzzzzzzzzzzzzzzzmk",
    "kmzzzzzzzzzzzzzzzzzzzzzzzzmk",
    "kmzzzzzzzzzzzzzzzzzzzzzzzzmk",
    "kmzzzzzzzzzzzzzzzzzzzzzzzzmk",
    "kmzzzzzzzzzzzzzzzzzzzzzzzzmk",
    "kmzzzzzzzzzzzzzzzzzzzzzzzzmk",
    "kmzzzzzzzzzzzzzzzzzzzzzzzzmk",
    "kmzzzzzzzzzzzzzzzzzzzzzzzzmk",
    "kmzzzzzzzzzzzzzzzzzzzzzzzzmk",
    "kmmmmmmmmmmmmmmmmmmmmmmmmmmk",
    "kkkkkkkkkkkkkkkkkkkkkkkkkkkk",
    "...km..................mk...",
    "...km..................mk...",
    "..kkkk................kkkk..",
]

S["table_round"] = [
    "......kkkkkkkkkkkkkkkk......",
    "...kkkmmmmmmmmmmmmmmmmkkk...",
    ".kkmmmmmmmmmmmmmmmmmmmmmmkk.",
    "kmmmmmmmmmmmmmmmmmmmmmmmmmmk",
    "kssmmmmmmmmmmmmmmmmmmmmmmssk",
    ".kksssssssssssssssssssssskk.",
    "...kkkkkkkkkkkkkkkkkkkkkk...",
    "............kssk............",
    "............kssk............",
    "..........kkkkkkkk..........",
]

S["blueprint"] = [
    "kkkkkkkkkkkkkkkkkk",
    "kbbbbbbbbbbbbbbbbk",
    "kbwwwwwwbbbwbbbbbk",
    "kbwbbbbwbbbwbbbbbk",
    "kbwbbbbwwwwwwwwbbk",
    "kbwbbbbwbbbbbbwbbk",
    "kbwwwwwwbbbbbbwbbk",
    "kbbbbbbbbbwwwwwbbk",
    "kbbwwbbbbbbbbbbbbk",
    "kkkkkkkkkkkkkkkkkk",
]

S["workbench"] = [
    "kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk",
    "kmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmk",
    "kssssssssssssssssssssssssssssssk",
    "kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk",
    ".ks.........................sk..",
    ".ks.........................sk..",
    ".ks.........................sk..",
    ".ks.........................sk..",
    ".ks.........................sk..",
    ".ks.........................sk..",
    "kkkk.......................kkkk.",
]

S["scorecard_9"] = [
    "kkkkkkkkk",
    "kwwwwwwwk",
    "kwwkkkwwk",
    "kwkwwwkwk",
    "kwwkkkkwk",
    "kwwwwwkwk",
    "kwwkkkwwk",
    "kwwwwwwwk",
    "kkkkkkkkk",
    "....k....",
    "....k....",
    "....k....",
]
S["scorecard_7"] = [
    "kkkkkkkkk",
    "kwwwwwwwk",
    "kwkkkkkwk",
    "kwwwwwkwk",
    "kwwwwkwwk",
    "kwwwkwwwk",
    "kwwwkwwwk",
    "kwwwwwwwk",
    "kkkkkkkkk",
    "....k....",
    "....k....",
    "....k....",
]

S["trophy"] = [
    "..kkkkkkkk..",
    "kkkyyyyyykkk",
    "kyk.yywyy.ky",
    "kyk.yywyy.ky",
    ".kykyyyyykyk",
    "..kkyyyyykk.",
    "....kyyyk...",
    ".....kyk....",
    ".....kyk....",
    "....kkkkk...",
    "...kmmmmmk..",
    "...kmyyymk..",
    "..kkkkkkkkk.",
]

S["trophy_cutout"] = [
    "..kkkkkkkk..",
    "kkkzzzzzzkkk",
    "kzk.zzazz.kz",
    "kzk.zzazz.kz",
    ".kzkzzzzzkzk",
    "..kkzzzzzkk.",
    "....kzzzk...",
    ".....kzk....",
    ".....kzk....",
    "....kkkkk...",
    "...kzzzzzk..",
    "...kzaazzk..",
    "..kkkkkkkkk.",
]

S["magnifier"] = [
    "..kkkk....",
    ".kbwwbk...",
    "kbwbbbbk..",
    "kwbbbbbk..",
    "kbbbbbbk..",
    ".kbbbbk...",
    "..kkkkmk..",
    "......kmk.",
    ".......kmk",
    "........kk",
]

# --- Home Lab -------------------------------------------------------------

S["server"] = [
    "kkkkkkkkkkkk",
    "kddddddddddk",
    "kdkkkkkkklgk",
    "kddddddddddk",
    "kdkkkkkkkogk",
    "kddddddddddk",
    "kdkkkkkkklgk",
    "kddddddddddk",
    "kdkkkkkkklgk",
    "kddddddddddk",
    "kdkkkkkkkbgk",
    "kddddddddddk",
    "kdkkkkkkklgk",
    "kddddddddddk",
    "kkkkkkkkkkkk",
    ".kk......kk.",
]

S["nas"] = [
    "kkkkkkkkkkkkkk",
    "keeeeeeeeeeeek",
    "kekdkdkdkdkdek",
    "kekdkdkdkdkdek",
    "kekdkdkdkdkdek",
    "kekdkdkdkdkdek",
    "keeeeeeeeeeeek",
    "kelebeeeeeeeek",
    "keeeeeeeeeeeek",
    "kkkkkkkkkkkkkk",
]

S["laptop"] = [
    "..kkkkkkkkkk..",
    "..knnnnnnnnk..",
    "..knbbnnnnnk..",
    "..knnnlnnnnk..",
    "..knnnnnnnnk..",
    "..kkkkkkkkkk..",
    "kkggggggggggkk",
    "kddddddddddddk",
    "kkkkkkkkkkkkkk",
]

S["plant"] = [
    "...l..l.",
    "..ltl.tl",
    ".lttlltl",
    "..ltttl.",
    "...ttl..",
    "..kkkkk.",
    "..kmmmk.",
    "..kmmmk.",
    "...kkk..",
]

S["lamp"] = [
    "....kkkk....",
    "...kyyyyk...",
    "...kyyyyk...",
    "..kyyyyyyk..",
    "..kyyyyyyk..",
    ".kyyyyyyyyk.",
    ".kkkkkkkkkk.",
    ".....kk.....",
    ".....kk.....",
    ".....kk.....",
    ".....kk.....",
    ".....kk.....",
    "...kkkkkk...",
    "..kddddddk..",
    "..kkkkkkkk..",
]

S["lamp_off"] = [row.replace("y", "d") for row in S["lamp"]]

S["window_night"] = [
    "kkkkkkkkkkkkkk",
    "knnnnnnknnnnnk",
    "knnwnnnknnnnnk",
    "knnnnnnknnnynk",
    "knnnnnnknnyynk",
    "kkkkkkkkkkkkkk",
    "knnnnwnknnnnnk",
    "knnnnnnknnnwnk",
    "knnnnnnknnnnnk",
    "kkkkkkkkkkkkkk",
]

S["mug"] = [
    "..w..w...",
    ".w..w....",
    "kkkkkk...",
    "kwwwwkkk.",
    "kwrrwk.k.",
    "kwrrwk.k.",
    "kwwwwkkk.",
    "kwwwwk...",
    ".kkkk....",
]

# --- Signals and noise ----------------------------------------------------

S["megaphone"] = [
    "..........kk..",
    "........kkrk..",
    "......kkrrrk..",
    "kkkkkkrrrrrk..",
    "kwwwwkrrrrrk.y",
    "kwwwwkrrrrrk..",
    "kkkkkkrrrrrk.y",
    "....kkkkrrrk..",
    "....kk..kkrk..",
    "....kk....kk..",
]

S["bubble_alert"] = [
    ".kkkkkkkk.",
    "kwwwwwwwwk",
    "kwwwrrwwwk",
    "kwwwrrwwwk",
    "kwwwrrwwwk",
    "kwwwwwwwwk",
    "kwwwrrwwwk",
    "kwwwwwwwwk",
    ".kkkkkkkk.",
    "..kwk.....",
    "..kk......",
]

S["bubble_ok"] = [
    ".kkkkkkkk.",
    "kwwwwwwwwk",
    "kwwwwwwtwk",
    "kwwwwwttwk",
    "kwtwwttwwk",
    "kwttttwwwk",
    "kwwttwwwwk",
    "kwwwwwwwwk",
    ".kkkkkkkk.",
    ".....kwk..",
    "......kk..",
]

S["bell"] = [
    "....kk....",
    "...kyyk...",
    "..kyyyyk..",
    "..kyyyyk..",
    ".kyyyyyyk.",
    ".kyyyyyyk.",
    "kyyyyyyyyk",
    "kkkkkkkkkk",
    "....kk....",
]

# --- Moving house ---------------------------------------------------------

S["box"] = [
    "kkkkkkkkkk",
    "kzzzzazzzk",
    "kzzzzazzzk",
    "kkkkkkkkkk",
    "kzzzzazzzk",
    "kzzzzzzzzk",
    "kzwwwwzzzk",
    "kzzzzzzzzk",
    "kkkkkkkkkk",
]

S["truck"] = [
    "kkkkkkkkkkkkkkkkkkkkk...........",
    "kwwwwwwwwwwwwwwwwwwwk...........",
    "kwwwwwwwwwwwwwwwwwwwkkkkkkk.....",
    "kwwbbbwwwwwwwwwwwwwwkbbbbbbk....",
    "kwwbbbwwwwwwwwwwwwwwkbbbbbbbk...",
    "kwwwwwwwwwwwwwwwwwwwkbbbbbbbbk..",
    "kwwwwwwwwwwwwwwwwwwwkkkkkkkkkkk.",
    "kwwwwwwwwwwwwwwwwwwwkrrrrrrrrrrk",
    "kwwwwwwwwwwwwwwwwwwwkrrrrrrrrryk",
    "kkkkkkkkkkkkkkkkkkkkkrrrrrrrrrrk",
    "krrrrrrrrrrrrrrrrrrrrrrrrrrrrrrk",
    "kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk",
    "...kkkk.............kkkk........",
    "..kddddk...........kddddk.......",
    "..kdggdk...........kdggdk.......",
    "...kkkk.............kkkk........",
]

S["house"] = [
    ".......kk.......",
    "......krrk......",
    ".....krrrrk.....",
    "....krrrrrrk....",
    "...krrrrrrrrk...",
    "..krrrrrrrrrrk..",
    ".kkkkkkkkkkkkkk.",
    "..kwwwwwwwwwwk..",
    "..kwbbwwwwbbwk..",
    "..kwbbwwwwbbwk..",
    "..kwwwwmmwwwwk..",
    "..kwwwwmmwwwwk..",
    "..kwwwwmmwwwwk..",
    "..kkkkkkkkkkkk..",
]

S["mirror"] = [
    "....kkkkkkkk....",
    "..kkyyyyyyyykk..",
    ".kyykkkkkkkkyyk.",
    ".kykbbbbbbbbkyk.",
    "kyykbwbbbbbbkyyk",
    "kykbbbwbbbbbbkyk",
    "kykbbbbbbbbbbkyk",
    "kykbbbbbbbbbbkyk",
    "kykbbbbbbbbbbkyk",
    "kykbbbbbbbbbbkyk",
    "kykbbbbbbbbbbkyk",
    "kykbbbbbbbbbbkyk",
    "kykbbbbbbbbbbkyk",
    "kykbbbbbbbbbbkyk",
    "kyykbbbbbbbbkyyk",
    ".kykbbbbbbbbkyk.",
    ".kyykkkkkkkkyyk.",
    "..kkyyyyyyyykk..",
    "....kkkkkkkk....",
    "......kmmk......",
    "....kkmmmmkk....",
    "...kmmmmmmmmk...",
]

S["signpost"] = [
    ".....kk.....",
    "kkkkkkkkkkk.",
    "kmmmmmmmmmmk",
    "kmwwmwwmwmk.",
    "kkkkkkkkkkk.",
    ".kkkkkkkkkkk",
    "kmmmmmmmmmmk",
    ".kmwwmwmwwmk",
    ".kkkkkkkkkkk",
    ".....km.....",
    ".....km.....",
    ".....km.....",
    ".....km.....",
    "....kkkk....",
]

S["calendar"] = [
    "kkkkkkkkkkk",
    "krrrrrrrrrk",
    "krwrrrrrwrk",
    "kkkkkkkkkkk",
    "kwwwwwwwwwk",
    "kwkwkwkwkwk",
    "kwwwwwwwwwk",
    "kwkwkwkwkwk",
    "kwwwwwwwwwk",
    "kwkwkwrwwwk",
    "kkkkkkkkkkk",
]

S["heart"] = [
    ".kk.kk.",
    "krrkrrk",
    "krrrrrk",
    "krrrrrk",
    ".krrrk.",
    "..krk..",
    "...k...",
]

S["spark"] = [
    "...y...",
    "...y...",
    "..yyy..",
    "yyywyyy",
    "..yyy..",
    "...y...",
    "...y...",
]

# --- Sky and nature -------------------------------------------------------

S["sun"] = [
    "......y......",
    "......y......",
    "..y.......y..",
    "...y.kkk.y...",
    "....kyyyk....",
    "...kyyyyyk...",
    "yy.kyyyyyk.yy",
    "...kyyyyyk...",
    "....kyyyk....",
    "...y.kkk.y...",
    "..y.......y..",
    "......y......",
    "......y......",
]

S["moon"] = [
    "...kkkk...",
    "..kwwwwk..",
    ".kwwwkk...",
    "kwwwk.....",
    "kwwwk.....",
    "kwwwk.....",
    ".kwwwkk...",
    "..kwwwwk..",
    "...kkkk...",
]

S["star"] = [
    ".y.",
    "yyy",
    ".y.",
]

S["cloud"] = [
    "......kkkk......",
    "....kkwwwwkk....",
    "..kkwwwwwwwwk...",
    ".kwwwwwwwwwwwkk.",
    "kwwwwwwwwwwwwwwk",
    "kwwwwwwwwwwwwwwk",
    ".kkkkkkkkkkkkkk.",
]

S["raincloud"] = [
    "......kkkk......",
    "....kkggggkk....",
    "..kkggggggggk...",
    ".kgggggggggggkk.",
    "kggggggggggggggk",
    ".kkkkkkkkkkkkkk.",
    "..b...b...b...b.",
    ".b...b...b...b..",
    "..b...b...b...b.",
]

S["tree"] = [
    "....kkkk....",
    "..kkllllkk..",
    ".klllltlllk.",
    "kllltllllllk",
    "klltlllltllk",
    "klllllltlllk",
    ".kllltllllk.",
    "..kkllllkk..",
    "....kmmk....",
    "....kmmk....",
    "....kmmk....",
    "...kkkkkk...",
]

S["waves"] = [
    "..bb......bb......bb......bb....",
    ".bwwb....bwwb....bwwb....bwwb...",
    "bbbbbb..bbbbbb..bbbbbb..bbbbbb..",
    "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "nbbbbbbnbbbbbbbnbbbbbbbnbbbbbbbn",
    "nnbbbbnnnbbbbnnnnbbbbnnnnbbbbnnn",
    "nnnnbnnnnnnnbnnnnnnnbnnnnnnnbnnn",
    "nnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn",
    "nnnbnnnnnnnnnnnbnnnnnnnnnnnbnnnn",
    "nnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn",
]

S["book_closed"] = [
    "kkkkkkkkkkk.",
    "kvvvvvvvvvkk",
    "kvwwwwwwwvkw",
    "kvvvvvvvvvkw",
    "kvvyyyyvvvkw",
    "kvvvvvvvvvkw",
    "kvvvvvvvvvkw",
    "kkkkkkkkkkkw",
    ".kwwwwwwwwwk",
    "..kkkkkkkkkk",
]

S["hill"] = [
    "..........kkkkkkkkkkkk..........",
    "......kkkktttttttttttkkkk.......",
    "...kkkttttttttlttttttttttkkk....",
    ".kkttttlttttttttttttltttttttkk..",
    "kttttttttttttttlttttttttttttttk.",
    "ktttlttttttttttttttttttlttttttk.",
]

# --- Distinct settings and story props ------------------------------------

S["map_wall"] = [
    "kkkkkkkkkkkkkkkkkkkk",
    "kmmmmmmmmmmmmmmmmmmk",
    "kmwwwwwwwwkwwwwwwwmk",
    "kmwbbbbbwwkwtttttwwk",
    "kmwbbllbwwkwttllttwk",
    "kmwbbbbbwwkwtttttwwk",
    "kmkkkkkkkkkkkkkkkkmk",
    "kmwwwwwwwwkwwwwwwwmk",
    "kmwooooowwkwuuuuuwwk",
    "kmwoyyoowwkwuuppuuwk",
    "kmwwwwwwwwkwwwwwwwmk",
    "kmmmmmmmmmmmmmmmmmmk",
    "kkkkkkkkkkkkkkkkkkkk",
]

S["drafting_table"] = [
    "....kkkkkkkkkkkkkkkkkkkkkkkk....",
    "..kkwwwwwwwwwwwwwwwwwwwwwwwwkk..",
    "kkmmmmmmmmmmmmmmmmmmmmmmmmmmmmkk",
    "kssssssssssssssssssssssssssssssk",
    "kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk",
    "..ks........................sk..",
    "..ks....kkkkkkkkkkkkkkkk....sk..",
    "..ks....kssssssssssssssk....sk..",
    "..ks....ks............sk....sk..",
    "..ks....ks............sk....sk..",
    ".kkkk..kkkk..........kkkk..kkkk.",
]

S["compass_rose"] = [
    "......kk......",
    ".....kyyk.....",
    "....kyyyyk....",
    "...kkbbbbkk...",
    "..kbbwwwwbbk..",
    ".kbbwrrrrwbbk.",
    "kyywrkkkkwryyk",
    "kyywrkkkkwryyk",
    ".kbbwrrrrwbbk.",
    "..kbbwwwwbbk..",
    "...kkbbbbkk...",
    "....kyyyyk....",
    ".....kmmk.....",
    "...kkmmmmkk...",
]

S["telescope"] = [
    "..........kkkk..",
    "........kkyyyyk.",
    "......kkyyyyyyyk",
    "....kkyyyyyyykk.",
    "..kkyyyyyyykk...",
    "kkyyyyyyykk.....",
    "kyyyyyykk.......",
    ".kkkkkk.........",
    "....kmmk........",
    "...km..mk.......",
    "..km....mk......",
    ".km......mk.....",
    "kkk......kkk....",
]

S["memory_dome"] = [
    "....kkkkkkkk....",
    "..kkbbbbbbbbkk..",
    ".kbbwwwwbbbbbbk.",
    "kbbwppppppbbbbbk",
    "kbbppppppppbbbbk",
    "kbbppwwwwppbbbbk",
    "kbbppppppppbbbbk",
    ".kbbppppppbbbbk.",
    "..kkkkkkkkkkkk..",
    "..kddddddddddk..",
    ".kkmmmmmmmmmmkk.",
    "kssssssssssssssk",
    "kkkkkkkkkkkkkkkk",
]

S["radar_screen"] = [
    "kkkkkkkkkkkkkkkkkkkkkk",
    "kddddddddddddddddddddk",
    "kdkkkkkkkkkkkkkkkkkkdk",
    "kdknnnnnnnkknnnnnnnkdk",
    "kdknnlbnnnkknnllnnnkdk",
    "kdknnnlnnnkknlwwlnnkdk",
    "kdknnlllnnkknnllnnnkdk",
    "kdknnnnnnnkknnnnnnnkdk",
    "kdkkkkkkkkkkkkkkkkkkdk",
    "kddllooooddddddllooddk",
    "kkkkkkkkkkkkkkkkkkkkkk",
]

S["server_pair"] = [
    ".kkkkkkkkkkkk..kkkkkkkkkkkk.",
    "kzzzzzzzzzzzzkkzzzzzzzzzzzzk",
    "kzddddddddddzkkzddddddddddzk",
    "kzdkkkkkkkldzkkzdkkkkkkkldzk",
    "kzddddddddddzkkzddddddddddzk",
    "kzdkkkkkkkodzkkzdkkkkkkkodzk",
    "kzddddddddddzkkzddddddddddzk",
    "kzzzzzzzzzzzzkkzzzzzzzzzzzzk",
    "kkkkkkkkkkkkkkkkkkkkkkkkkkkk",
    "kssssssssssssssssssssssssssk",
    ".kk......................kk.",
    ".kk......................kk.",
]

S["mail_chute"] = [
    "kkkkkkkkkkkkkkkkkkkkkkkk",
    "kmmmmmmmmmmmmmmmmmmmmmmk",
    "kmsssskmsssskmsssskmssmk",
    "kmswwskmsyyskmsbbskmspsk",
    "kmswwskmsyyskmsbbskmspsk",
    "kmmmmmmmmmmmmmmmmmmmmmmk",
    "kmsssskmsssskmsssskmssmk",
    "kmsllskmswwskmsooskmswsk",
    "kmsllskmswwskmsooskmswsk",
    "kmmmmmmmmmmmmmmmmmmmmmmk",
    "kmsssskmsssskmsssskmssmk",
    "kmsbbskmsrrskmswwskmsysk",
    "kmsbbskmsrrskmswwskmsysk",
    "kmmmmmmmmmmmmmmmmmmmmmmk",
    "kkkkkkkkkkkkkkkkkkkkkkkk",
    ".kk..................kk.",
]

S["conveyor"] = [
    "kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk",
    "kddddddddddddddddddddddddddddddk",
    "kdggddggddggddggddggddggddggddgk",
    "kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk",
    "..kddk....................kddk..",
    "..kddk....................kddk..",
    "..kddk....................kddk..",
    "..kddk....................kddk..",
    ".kkkkkk..................kkkkkk.",
]

S["video_card"] = [
    "kkkkkkkkkkkkkk",
    "krrrrrrrrrrrrk",
    "krrrrrrrrrrrrk",
    "krrrrwrrrrrrrk",
    "krrrrwwrrrrrrk",
    "krrrrwwwrrrrrk",
    "krrrrwwrrrrrrk",
    "krrrrwrrrrrrrk",
    "krrrrrrrrrrrrk",
    "kkkkkkkkkkkkkk",
]

S["chandelier"] = [
    ".........kk.........",
    ".........kk.........",
    "..ww.....kk.....ww..",
    "..yy.....kk.....yy..",
    ".kkkk...kkkk...kkkk.",
    ".kyyk..kyyyyk..kyyk.",
    "..kkykkkyyyykkyykk..",
    "...kkyyyyyyyyyykk...",
    ".....kkkkkkkkkk.....",
    ".........kk.........",
]

S["scales"] = [
    ".......kkkk.......",
    "......kyyyyk......",
    ".kkkkkkkkkkkkkkkk.",
    "kyyyyyyyyyyyyyyyyk",
    ".kk....kyyk....kk.",
    ".k.k...kyyk...k.k.",
    "k...k..kyyk..k...k",
    "kkkkkk.kyyk.kkkkkk",
    "kyyyyk.kyyk.kyyyyk",
    ".kkkk..kyyk..kkkk.",
    "......kmmmmk......",
    "....kkmmmmmmkk....",
    "...kkkkkkkkkkkk...",
]

S["scoreboard"] = [
    "kkkkkkkkkkkkkkkkkkkkkkkk",
    "kddddddddddddddddddddddk",
    "kdkkkkkkkkkkkkkkkkkkkkdk",
    "kdknnllnnkknnookknnrrkdk",
    "kdknnlwnnkknnoWkknnrrkdk".replace("W", "w"),
    "kdknnllnnkknnookknnrrkdk",
    "kdknnnnnnkknnnnkknnnnkdk",
    "kdkkkkkkkkkkkkkkkkkkkkdk",
    "kddddddddddddddddddddddk",
    "kkkkkkkkkkkkkkkkkkkkkkkk",
]

S["podium_steps"] = [
    "........kkkkkkkk........",
    "........kyyyyyyk........",
    "........kywwwwyk........",
    "kkkkkkkkkywkwwyk........",
    "kgggggggkywkwwykkkkkkkkk",
    "kgwwwwwwkyyyyyykmmmmmmmk",
    "kgwwwwwwkzzzzzzkmwwwwmmk",
    "kgwwwwwwkzzzzzzkmwwwwmmk",
    "kgwwwwwwkzzzzzzkmwwwwmmk",
    "kkkkkkkkkkkkkkkkkkkkkkkk",
]

S["hurdle"] = [
    "kkkkkkkkkkkkkkkk",
    "krrwwrrwwrrwwrrk",
    "krrwwrrwwrrwwrrk",
    "kkkkkkkkkkkkkkkk",
    ".kk..........kk.",
    ".kk..........kk.",
    ".kk..........kk.",
    ".kk..........kk.",
    "kkkk........kkkk",
]

S["gavel_bench"] = [
    "kkkkkkkkkkkkkkkkkkkkkkkkkkkk",
    "kYYYYYYYYYYYYYYYYYYYYYYYYYYk".replace("Y", "y"),
    "kmmmmmmmmmmmmmmmmmmmmmmmmmmk",
    "kssssssssssssssssssssssssssk",
    "ksmmmmmmmmmmmmmmmmmmmmmmmmsk",
    "ksmmssssmmmmmmmmmmmmssssmmsk",
    "ksmmssssmmmmmmmmmmmmssssmmsk",
    "ksmmmmmmmmmmmmmmmmmmmmmmmmsk",
    "kssssssssssssssssssssssssssk",
    "kkkkkkkkkkkkkkkkkkkkkkkkkkkk",
]

S["recycle_bin"] = [
    ".kkkkkkkkkkkk.",
    "kddddddddddddk",
    ".kkkkkkkkkkkk.",
    ".kttttttttttk.",
    ".ktllttttlltk.",
    ".ktlwwwwwwltk.",
    ".kttwwttwwttk.",
    ".kttwwwwwwttk.",
    ".kttttttttttk.",
    ".ktllttttlltk.",
    ".kttttttttttk.",
    "..kkkkkkkkkk..",
]

S["clock_wall"] = [
    "...kkkkkk...",
    ".kkwwwwwwkk.",
    "kwwwwkkwwwwk",
    "kwwwwkkwwwwk",
    "kwwkkkkewwwk",
    "kwwwwkkkwwwk",
    "kwwwwwwwwwwk",
    "kwwwwwwwwwwk",
    ".kkwwwwwwkk.",
    "...kkkkkk...",
]

S["anvil_forge"] = [
    "..kkkkkkkkkkkkkkkk..",
    "kkddddddddddddddddkk",
    "kggggddddddddddddddk",
    ".kkkkddddddddddddkk.",
    "....kkkddddddddkk...",
    "......kkddddddkk....",
    "....kkkkddddddkkkk..",
    "..kkddddddddddddddkk",
    ".kssssssssssssssssk.",
    ".kkkkkkkkkkkkkkkkkk.",
]

S["bridge_arch"] = [
    "......kkkkkkkkkkkkkkkkkkkk......",
    "...kkkzzzzzzzzzzzzzzzzzzzzkkk...",
    ".kkzzzzaaaazzzzaaaazzzzaaaazzkk.",
    "kzzzzaaaazzzzaaaazzzzaaaazzzzzzk",
    "kzzaaaazzzzzzaaaazzzzzzaaaazzzzk",
    "kzzzzzzzzkkkkkkkkkkkkkkzzzzzzzzk",
    "kzzzzzzkk..............kkzzzzzzk",
    "kzzzzkk..................kkzzzzk",
    "kkkkk......................kkkkk",
]

S["parliament_roof"] = [
    "...........kk...........",
    "...........krkk.........",
    "...........krrrk........",
    "...........kk...........",
    "..........kggk..........",
    "........kkggggkk........",
    "......kkgg....ggkk......",
    "....kkgg........ggkk....",
    "..kkgg............ggkk..",
    "kkkkkkkkkkkkkkkkkkkkkkkk",
    "kzzzzzzzzzzzzzzzzzzzzzzk",
    "kkkkkkkkkkkkkkkkkkkkkkkk",
]

S["hansard_desk"] = [
    "..kkkkkkkkkkkkkkkkkkkkkkkkkkkk..",
    ".kttttttttttttttttttttttttttttk.",
    "kttllllllllllllllllllllllllllttk",
    "kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk",
    "kmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmk",
    "kssssssssssssssssssssssssssssssk",
    ".ks..........................sk.",
    ".ks..........................sk.",
    "..kkkkkkkkkkkkkkkkkkkkkkkkkkkk..",
]

S["robot_arm"] = [
    "......kkkkkk....",
    "....kkooooook...",
    "...koookkkkook..",
    "..kook....kkook.",
    "..kook.....kkkk.",
    "...kook....kddk.",
    "....kook...kyyk.",
    "...kkoook.......",
    "..kooooook......",
    ".kddddddddk.....",
    "kkkkkkkkkkkk....",
]

S["timber_frame"] = [
    "kkkkkkkkkkkkkkkkkkkk",
    "kzzzzzzzzzzzzzzzzzzk",
    "kzkzzzzzzzkzzzzzzkzk",
    "kzkz..k..zkz..k..kzk",
    "kzkz...k.zkz.k...kzk",
    "kzkzzzzzzzkzzzzzzkzk",
    "kzzzzzzzzzzzzzzzzzzk",
    "kzkzzzzzzzkzzzzzzkzk",
    "kzkz..k..zkz..k..kzk",
    "kzkz...k.zkz.k...kzk",
    "kzkzzzzzzzkzzzzzzkzk",
    "kzzzzzzzzzzzzzzzzzzk",
    "kkkkkkkkkkkkkkkkkkkk",
]

S["weight_scale"] = [
    "..........kkkk..........",
    ".........kddddk.........",
    "kkkkkkkkkkkkkkkkkkkkkkkk",
    "kggggggggggggggggggggggk",
    ".kk........kk........kk.",
    "k..k.......kk.......k..k",
    "kkkkkk.....kk.....kkkkkk",
    "knnnnk.....kk.....kllllk",
    "knwwnk.....kk.....klwwlk",
    "knnnnk....kkkk....kllllk",
    "kkkkkk..kkddddkk..kkkkkk",
    ".......kkkkkkkkkk.......",
]

S["portal_arch"] = [
    "....kkkkkkkkkkkkkkkk....",
    "..kkmmmmmmmmmmmmmmmmkk..",
    ".kmmmmwwwwwwwwwwwwmmmmk.",
    "kmmmwwwwwwwwwwwwwwwwmmmk",
    "kmmwwwwkkkkkkkkkkwwwwmmk",
    "kmmwwwk..........kwwwmmk",
    "kmmwwwk..........kwwwmmk",
    "kmmwwwk..........kwwwmmk",
    "kmmwwwk..........kwwwmmk",
    "kmmwwwk..........kwwwmmk",
    "kmmwwwk..........kwwwmmk",
    "kkkkkkk..........kkkkkkk",
]

S["radio_dish"] = [
    "....kkkkkk....",
    "..kkwwwwwwkk..",
    ".kwwggggggwwk.",
    "kwggbbbbbbggwk",
    "kwgbbkkkkbbgwk",
    ".kwgbk..kbgwk.",
    "..kwwk..kwwk..",
    "....kk..kk....",
    ".....kddk.....",
    "...kkddddkk...",
    "..kkkkkkkkkk..",
]

S["sandbox_pen"] = [
    "kkkkkkkkkkkkkkkkkkkkkkkk",
    "krrorroorroorroorroorrok",
    "kkkkkkkkkkkkkkkkkkkkkkkk",
    "kyyyyyyyyyyyyyyyyyyyyyyk",
    "kyzzzzzzzzzzzzzzzzzzzzyk",
    "kyzzyyyyyzzzzzzyyyyyzzyk",
    "kyzzzzzzzzzzzzzzzzzzzzyk",
    "kkkkkkkkkkkkkkkkkkkkkkkk",
]

S["coffee_table"] = [
    "..kkkkkkkkkkkkkkkkkkkk..",
    ".kmmmmmmmmmmmmmmmmmmmmk.",
    "kssssssssssssssssssssssk",
    "kkkkkkkkkkkkkkkkkkkkkkkk",
    "..ks................sk..",
    "..ks................sk..",
    "..ks................sk..",
    ".kkkk..............kkkk.",
]


def check(sprites):
    problems = []
    for name, rows in sprites.items():
        widths = {len(r) for r in rows}
        if len(widths) != 1:
            problems.append(f"{name}: uneven rows {sorted(widths)}")
        for r in rows:
            for ch in r:
                if ch != "." and ch not in PALETTE:
                    problems.append(f"{name}: unknown key {ch!r}")
                    break
    return problems


def sheet(sprites, path, scale=6, pad=4):
    from PIL import Image, ImageDraw

    cols = 6
    names = list(sprites)
    cellw = max(len(r[0]) for r in sprites.values()) * scale + pad * 2
    cellh = max(len(r) for r in sprites.values()) * scale + pad * 2 + 12
    rows = (len(names) + cols - 1) // cols
    img = Image.new("RGB", (cols * cellw, rows * cellh), "#e9e1cf")
    draw = ImageDraw.Draw(img)
    for i, name in enumerate(names):
        ox = (i % cols) * cellw + pad
        oy = (i // cols) * cellh + pad
        draw.text((ox, oy), name, fill="#241f2e")
        for y, row in enumerate(sprites[name]):
            for x, ch in enumerate(row):
                if ch == ".":
                    continue
                c = PALETTE[ch]
                draw.rectangle(
                    [ox + x * scale, oy + 12 + y * scale, ox + (x + 1) * scale - 1, oy + 12 + (y + 1) * scale - 1],
                    fill=c,
                )
    img.save(path)


def main(argv):
    problems = check(S)
    if problems:
        print("\n".join(problems))
        return 1
    out = ROOT / "engine" / "library" / "sprites.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"palette": PALETTE, "sprites": S}, indent=1) + "\n")
    print(f"wrote {out} with {len(S)} sprites")
    if "--sheet" in argv:
        dest = argv[argv.index("--sheet") + 1]
        sheet(S, dest)
        print(f"sheet {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
