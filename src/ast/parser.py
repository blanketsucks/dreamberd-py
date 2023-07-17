from typing import List, Set, Optional

from .ast import *
from src.tokens import Token, TokenType, KEYWORDS_TO_STR
from src.errors import error
from src.lexer import EQ_TYPE_DEPTH

EQ_TYPES = (TokenType.Assign, *EQ_TYPE_DEPTH)

BINARY_OPS = (
    TokenType.Plus, TokenType.Minus, TokenType.Mul, TokenType.Div,
    TokenType.Assign, TokenType.Eq, TokenType.TripleEq, TokenType.QuadEq
)

UNARY_OPS = (
    TokenType.SemiColon, TokenType.Minus
)

class Parser:
    def __init__(self, tokens: List[Token]) -> None:
        self.tokens = tokens
        self.index = -1

        self.current: Token = None # type: ignore
        self.next()

        self.deleted: Set[TokenType] = set()

    def next(self, ignore_whitespace: bool = False) -> None:
        self.index += 1
        if self.index < len(self.tokens):
            self.current = self.tokens[self.index]

            if ignore_whitespace and self.current.type is TokenType.Whitespace:
                self.next(ignore_whitespace=True)
        else:
            self.current = Token(TokenType.EOF, '\0', self.current.span)
        
    def peek(self) -> Token:
        if self.index + 1 < len(self.tokens):
            return self.tokens[self.index + 1]

        return Token(TokenType.EOF, '\0', self.current.span)

    def expect(self, type: TokenType, message: str, ignore_whitespace: bool = False) -> Token:
        if self.current.type is not type:
            error(self.current.span, f'Expected {message}')

        token = self.current
        self.next(ignore_whitespace=ignore_whitespace)

        return token

    def expect_boldness(self) -> int:
        boldness = 0
        while self.current.type is TokenType.Not:
            self.next()
            boldness += 1

        return boldness

    def parse(self) -> List[ASTExpr]:
        stmts = []
        while self.current.type is not TokenType.EOF:
            if self.current.type is TokenType.Whitespace:
                self.next()
                continue

            stmts.append(self.statement())

            while self.current.type is TokenType.Whitespace:
                self.next()

        return stmts
    
    def parse_variable_definition(self) -> ASTExpr:
        current = self.current
        self.next(True)

        next = self.current

        if current.type is TokenType.Var and next.type is TokenType.Var:
            type = VariableType.VarVar
        elif current.type is TokenType.Const and next.type is TokenType.Var:
            type = VariableType.ConstVar
        elif current.type is TokenType.Var and next.type is TokenType.Const:
            type = VariableType.VarConst
        elif current.type is TokenType.Const and next.type is TokenType.Const:
            type = VariableType.ConstConst
        else:
            error(self.current.span, f'Expected var or const')

        self.next(True)
        if self.current.type is TokenType.Const and type is VariableType.ConstConst:
            type = VariableType.ConstConstConst
            self.next(True)
            
        if self.current.type is TokenType.Int:
            name, span = self.current.value, self.current.span
            self.next(True)
        else:
            token = self.expect(TokenType.Ident, 'identifier', True)
            name, span = token.value, token.span

        if self.current.type is TokenType.Colon:
            # Type annotations do nothing so we just ignore them
            while self.current.type is not TokenType.Assign:
                self.next(True)

        self.expect(TokenType.Assign, '=', True)
        expr = VariableExpr(span, name, self.expr(False), type)

        if self.current.type is TokenType.InverseNot:
            boldness = -1

            while self.current.type is TokenType.InverseNot:
                self.next(True)
        else:
            boldness = self.expect_boldness()
            if boldness < 1:
                error(self.current.span, 'Expected !')

        expr.extras['boldness'] = boldness
        return expr
    
    def parse_function_definition(self) -> ASTExpr:
        self.next(True)

        if self.current.type is TokenType.Int:
            name, span = self.current.value, self.current.span
            self.next(True)
        else:
            token = self.expect(TokenType.Ident, 'identifier', True)
            name, span = token.value, token.span

        self.expect(TokenType.LParen, '(', True)
        args = []
        while self.current.type is not TokenType.RParen:
            args.append(self.expect(TokenType.Ident, 'identifier', True).value)

            if self.current.type is TokenType.Colon:
                # Type annotations do nothing so we just ignore them
                while self.current.type not in (TokenType.Comma, TokenType.RParen):
                    self.next(True)

            if self.current.type is TokenType.RParen:
                break

            self.expect(TokenType.Comma, ',', True)

        self.next(True)
        self.expect(TokenType.Assign, '=', True); self.expect(TokenType.Gt, '>', True)

        if self.current.type is not TokenType.LBrace:
            return FunctionExpr(span, name, args, self.expr())

        self.expect(TokenType.LBrace, '{', True)
        body = []

        while self.current.type is not TokenType.RBrace:
            body.append(self.statement())
            if self.current.type is TokenType.RBrace:
                break

            while self.current.type is TokenType.Whitespace:
                self.next()

        self.next(True)
        return FunctionExpr(span, name, args, body)
    
    def statement(self) -> ASTExpr:
        if self.current.type in self.deleted:
            error(self.current.span, f'{self.current.value} has been delete')

        if self.current.type is TokenType.Delete:
            self.next(True)

            if self.current.type in (TokenType.Int, TokenType.String, TokenType.Bool):
                expr = DeleteExpr(self.primary())
            elif self.current.type in KEYWORDS_TO_STR:
                self.deleted.add(self.current.type)
                self.next(True)

                expr = ASTExpr(self.current.span) # Dummy expr
            else:
                error(self.current.span, f'Expected int, string, bool or keyword')

            boldness = self.expect_boldness()
            if boldness < 1:
                error(self.current.span, 'Expected !')

            return expr
        elif self.current.type in (TokenType.Var, TokenType.Const):
            return self.parse_variable_definition()
        elif self.current.type is TokenType.Assert:
            self.next(True)

            expr = self.expr(False)
            err: Optional[str] = None

            if self.current.type is TokenType.Comma:
                self.next(True)
                err = self.expect(TokenType.String, 'string', True).value

            boldness = self.expect_boldness()
            if boldness < 1:
                error(self.current.span, 'Expected !')

            return AssertExpr(expr, err)
        elif self.current.type is TokenType.QuintEq:
            span = self.current.span

            while self.current.type is not TokenType.Whitespace and self.current.type in EQ_TYPES:
                self.next(True)

            filename: Optional[str] = None
            if self.current.type is TokenType.Ident:
                filename = self.current.value
                self.next()

                if self.current.type is TokenType.Dot:
                    self.next()
                    filename += '.' + self.expect(TokenType.Ident, 'identifier', True).value

            while self.current.type in EQ_TYPES:
                self.next(True)

            return NewFileExpr(span, filename)
        elif self.current.type is TokenType.Export:
            self.next(True)

            token = self.expect(TokenType.Ident, 'identifier', True)
            symbol, span = token.value, token.span

            self.expect(TokenType.To, 'to', True)
            filename = self.expect(TokenType.String, 'string', True).value

            boldness = self.expect_boldness()
            if boldness < 1:
                error(self.current.span, 'Expected !')

            return ExportExpr(span, symbol, filename)
        elif self.current.type is TokenType.Import:
            self.next(True)

            token = self.expect(TokenType.Ident, 'identifier', True)
            symbol, span = token.value, token.span

            boldness = self.expect_boldness()
            if boldness < 1:
                error(self.current.span, 'Expected !')

            return ImportExpr(span, symbol)
        elif self.current.type is TokenType.When:
            self.next(True)

            self.expect(TokenType.LParen, '(', True)
            cond = self.expr(False)

            self.expect(TokenType.RParen, ')', True)
            if not isinstance(cond, BinaryOpExpr):
                error(cond.span, 'Expected binary operator')
            
            self.expect(TokenType.LBrace, '{', True)
            body = []

            while self.current.type is not TokenType.RBrace:
                body.append(self.statement())
                if self.current.type is TokenType.RBrace:
                    break

                while self.current.type is TokenType.Whitespace:
                    self.next()

            self.next(True)
            return WhenExpr(cond.span, cond, body)
        elif self.current.type is TokenType.Function:
            return self.parse_function_definition()
        elif self.current.type is TokenType.Return:
            self.next(True)
            return ReturnExpr(self.expr())

        return self.expr()
    
    def expr(self, be_bold: bool = True) -> ASTExpr:
        lhs = self.unary()
        expr = self.binary(lhs)
        
        if be_bold:
            boldness = self.expect_boldness()
            if boldness < 1 and be_bold:
                error(self.current.span, 'Expected !')
        else:
            boldness = 0
        
        expr.extras['boldness'] = boldness
        return expr
    
    # This is probably super buggy but i won't bother testing/fixing it
    def binary(self, lhs: ASTExpr) -> ASTExpr:
        while True:
            is_whitespace_before = self.current.type is TokenType.Whitespace
            if is_whitespace_before:
                self.next()

            op = self.current.type
            if op not in BINARY_OPS:
                return lhs

            self.next()

            is_whitespace_after = self.current.type is TokenType.Whitespace
            if is_whitespace_after:
                self.next()

            rhs = self.unary()
            if is_whitespace_before and is_whitespace_after and self.current in BINARY_OPS:
                (lhs, rhs) = (self.binary(rhs), lhs)
            
            lhs = BinaryOpExpr(lhs, rhs, op)

    def unary(self) -> ASTExpr:
        if self.current.type not in UNARY_OPS:
            return self.primary()
    
        op = self.current.type
        self.next()

        expr = self.primary()
        return UnaryOpExpr(expr, op)

    def primary(self) -> ASTExpr:
        span = self.current.span

        if self.current.type is TokenType.Int:
            value = int(self.current.value)
            self.next()

            expr = IntegerExpr(span, value)
        elif self.current.type is TokenType.String:
            value = self.current.value
            self.next()

            return StringExpr(span, value)
        elif self.current.type is TokenType.Ident:
            value = self.current.value
            self.next()

            expr = IdentifierExpr(span, value)
        elif self.current.type is TokenType.Float:
            value = float(self.current.value)
            self.next()

            expr = FloatExpr(span, value)
        elif self.current.type is TokenType.LBracket:
            self.next(True)

            elements = []
            while self.current.type is not TokenType.RBracket:
                elements.append(self.expr(False))

                if self.current.type is TokenType.RBracket:
                    break

                self.expect(TokenType.Comma, ',', True)

            self.next(True)
            expr = ArrayExpr(span, elements)
        elif self.current.type is TokenType.LParen:
            self.next(True)
            expr = self.expr(False)

            self.expect(TokenType.RParen, ')', True)
        elif self.current.type is TokenType.Previous:
            self.next(True)
            expr = PreviousExpr(self.expr(False))
        else:
            raise Exception(f'Unexpected token: {self.current!r} at index {self.index}')
        
        if self.current.type is TokenType.LParen:
            self.next(True)

            args = []
            while self.current.type is not TokenType.RParen:
                args.append(self.expr(False))
                if self.current.type is TokenType.RParen:
                    break

                self.expect(TokenType.Comma, ',', True)

            self.next(True)
            expr = CallExpr(expr.span, expr, args)
        elif self.current.type is TokenType.LBracket:
            self.next(True)

            index = self.expr(False)
            self.expect(TokenType.RBracket, ']', True)

            expr = ArrayIndexExpr(expr.span, expr, index)

        return expr
        