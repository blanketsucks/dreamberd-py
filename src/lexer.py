from typing import Optional

from .tokens import Token, TokenType, KEYWORDS, SINGLE_CHAR_TOKENS, Location, Span

EQ_TYPE_DEPTH = [TokenType.Eq, TokenType.TripleEq, TokenType.QuadEq, TokenType.QuintEq]

class Lexer:
    def __init__(self, source: str, filename: str) -> None:
        self.source = source
        self.filename = filename

        self.index = -1
        self.line = 1
        self.column = 0

        self.current_char: str = None # type: ignore
        self.next()

    @property
    def location(self) -> Location:
        return Location(self.line, self.column, self.index)
    
    def make_span(self, start: Location, end: Optional[Location] = None) -> Span:
        if end is None:
            end = self.location

        lines = self.source.splitlines()
        line = lines[start.line - 1]


        return Span(start, end, self.filename, line)

    def next(self) -> None:
        self.index += 1
        self.column += 1

        if self.index < len(self.source):
            self.current_char = self.source[self.index]
        else:
            self.current_char = None # type: ignore

    def rewind(self) -> None:
        self.index -= 1
        self.column -= 1

        if self.index < len(self.source):
            self.current_char = self.source[self.index]
        else:
            self.current_char = None # type: ignore

    def peek(self) -> Optional[str]:
        if self.index + 1 < len(self.source):
            return self.source[self.index + 1]

        return None
    
    def parse_string(self) -> Token:
        start = self.location

        value = ""
        ending = self.current_char

        self.next()
        while self.current_char != ending:
            value += self.current_char
            self.next()

        end = self.location
        self.next()

        return Token(TokenType.String, value, self.make_span(start, end))
    
    def parse_number(self) -> Token:
        start = self.location
        value = ""

        while self.current_char and self.current_char.isdigit():
            value += self.current_char
            self.next()

        return Token(TokenType.Int, value, self.make_span(start)) 
    
    def parse_identifier(self) -> Token:
        start = self.location
        value = ""

        while self.current_char and self.current_char.isalnum():
            value += self.current_char
            self.next()

        if value in KEYWORDS:
            return Token(KEYWORDS[value], value, self.make_span(start))

        return Token(TokenType.Ident, value, self.make_span(start))
    
    def lex(self) -> Token:
        while self.current_char:
            start = self.location

            if self.current_char == '/':
                self.next()
                if self.current_char == '/':
                    self.next()
                    while self.current_char and self.current_char != '\n':
                        self.next()

                    continue

                self.rewind()

            if self.current_char in ('\'', '"'):
                return self.parse_string()
            elif self.current_char.isdigit():
                return self.parse_number()
            elif self.current_char.isalpha():
                return self.parse_identifier()
            elif self.current_char.isspace():
                if self.current_char == '\n':
                    self.line += 1
                    self.column = 0

                token = Token(TokenType.Whitespace, self.current_char, self.make_span(start))
                self.next()

                return token
            elif self.current_char in SINGLE_CHAR_TOKENS:
                token = Token(SINGLE_CHAR_TOKENS[self.current_char], self.current_char, self.make_span(start))
                self.next()

                return token
            elif self.current_char == '=':
                if self.peek() == '=':
                    self.next()
                    
                    depth = 0
                    while self.current_char == '=' and depth < 4:
                        self.next()
                        depth += 1

                    return Token(EQ_TYPE_DEPTH[depth - 1], '=' * (depth + 1), self.make_span(start))
                
                self.next()
                return Token(TokenType.Assign, '=', self.make_span(start))
            else:
                raise Exception(f'Unexpected character {self.current_char!r}')
            
        return Token(TokenType.EOF, "\0", self.make_span(self.location))
    
    def __iter__(self):
        return self
    
    def __next__(self) -> Token:
        token = self.lex()
        if token.type is TokenType.EOF:
            raise StopIteration

        return token
