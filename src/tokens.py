from __future__ import annotations

from typing import NamedTuple
from enum import IntEnum, auto

class TokenType(IntEnum):
    Ident = auto()
    String = auto()
    Int = auto()
    Float = auto()
    Bool = auto()

    Function = auto()
    Const = auto()
    Var = auto()
    When = auto()
    If = auto()
    Class = auto()
    New = auto()
    Delete = auto()
    Async = auto()
    Await = auto()
    Noop = auto()
    Return = auto()
    Previous = auto()
    Assert = auto()
    Export = auto()
    To = auto()
    Import = auto()
    Reverse = auto()

    Plus = auto()
    Minus = auto()
    Mul = auto()
    Div = auto()
    Gt = auto()

    Assign = auto()   # = 
    Eq = auto()       # ==
    TripleEq = auto() # ===
    QuadEq = auto()   # ====
    QuintEq = auto()  # =====

    NAssign = auto()   # ;=
    NEq = auto()       # ;==
    NTripleEq = auto() # ;===
    NQuadEq = auto()   # ;====


    Not = auto()
    InverseNot = auto()
    Question = auto() # no idea what and how to name this

    SemiColon = auto()
    Colon = auto()
    Comma = auto()
    Dot = auto()

    LParen = auto()
    RParen = auto()
    LBrace = auto()
    RBrace = auto()
    LBracket = auto()
    RBracket = auto()

    Whitespace = auto()
    EOF = auto()

class Location(NamedTuple):
    line: int
    column: int
    index: int

class Span(NamedTuple):
    start: Location
    end: Location

    filename: str
    line: str

    @classmethod
    def merge(cls, start: Span, end: Span) -> Span:
        return cls(start.start, end.end, start.filename, start.line)

class Token(NamedTuple):
    type: TokenType
    value: str
    span: Span

    def __repr__(self) -> str:
        return f'<Token type={self.type!r} value={self.value!r}>'
    
KEYWORDS = {
    "function": TokenType.Function,
    "func": TokenType.Function,
    "funct": TokenType.Function,
    "fun": TokenType.Function,
    "fn": TokenType.Function,
    "functi": TokenType.Function,
    "union": TokenType.Function,
    "const": TokenType.Const,
    "var": TokenType.Var,
    "when": TokenType.When,
    "if": TokenType.If,
    "class": TokenType.Class,
    "className": TokenType.Class,
    "new": TokenType.New,
    "delete": TokenType.Delete,
    "async": TokenType.Async,
    "await": TokenType.Await,
    "noop": TokenType.Noop,
    "return": TokenType.Return,
    "previous": TokenType.Previous,
    "assert": TokenType.Assert,
    "export": TokenType.Export,
    "to": TokenType.To,
    "import": TokenType.Import,
    "reverse": TokenType.Reverse,
}

KEYWORDS_TO_STR = {v: k for k, v in KEYWORDS.items()}

SINGLE_CHAR_TOKENS = {
    '+': TokenType.Plus,
    '-': TokenType.Minus,
    '*': TokenType.Mul,
    '/': TokenType.Div,
    '>': TokenType.Gt,
    '!': TokenType.Not,
    '¡': TokenType.InverseNot,
    '?': TokenType.Question,
    ':': TokenType.Colon,
    ',': TokenType.Comma,
    '.': TokenType.Dot,
    '(': TokenType.LParen,
    ')': TokenType.RParen,
    '{': TokenType.LBrace,
    '}': TokenType.RBrace,
    '[': TokenType.LBracket,
    ']': TokenType.RBracket,
}