from typing import Dict, Any, List, Optional, Tuple, Union

from enum import IntEnum

from src.tokens import TokenType, Span

__all__ = (
    'VariableType',
    'ASTExpr',
    'IntegerExpr',
    'FloatExpr',
    'StringExpr',
    'ArrayExpr',
    'DictExpr',
    'IndexExpr',
    'BinaryOpExpr',
    'UnaryOpExpr',
    'DeleteExpr',
    'IdentifierExpr',
    'VariableExpr',
    'FunctionExpr',
    'ReturnExpr',
    'CallExpr',
    'PreviousExpr',
    'AssertExpr',
    'NewFileExpr',
    'WhenExpr',
    'ExportExpr',
    'ImportExpr',
)


class VariableType(IntEnum):
    VarVar = 0
    VarConst = 1
    ConstVar = 2
    ConstConst = 3
    ConstConstConst = 4

class ASTExpr:
    span: Span

    def __init__(self, span: Span) -> None:
        self.extras: Dict[str, Any] = {}
        self.span = span

    def __repr__(self) -> str:
        return f'<ASTExpr>'

class IntegerExpr(ASTExpr):
    def __init__(self, span: Span, value: int) -> None:
        super().__init__(span)

        self.value = value

    def __repr__(self) -> str:
        return f'<IntegerExpr value={self.value}>'

class FloatExpr(ASTExpr):
    def __init__(self, span: Span, value: float) -> None:
        super().__init__(span)
        self.value = value

    def __repr__(self) -> str:
        return f'<FloatExpr value={self.value}>'
    
class StringExpr(ASTExpr):
    def __init__(self, span: Span, value: str) -> None:
        super().__init__(span)

        self.value = value

    def __repr__(self) -> str:
        return f'<StringExpr value={self.value!r}>'
    
class ArrayExpr(ASTExpr):
    def __init__(self, span: Span, values: List[ASTExpr]) -> None:
        super().__init__(span)

        self.values = values

    def __repr__(self) -> str:
        return f'<ArrayExpr values={self.values!r}>'
    
class DictExpr(ASTExpr):
    def __init__(self, span: Span, values: List[Tuple[ASTExpr, ASTExpr]]) -> None:
        super().__init__(span)

        self.values = values

    def __repr__(self) -> str:
        return f'<DictExpr values={self.values!r}>'

class IndexExpr(ASTExpr):
    def __init__(self, span: Span, value: ASTExpr, index: ASTExpr) -> None:
        super().__init__(span)

        self.value = value
        self.index = index

    def __repr__(self) -> str:
        return f'<IndexExpr value={self.value!r} index={self.index!r}>'

class BinaryOpExpr(ASTExpr):
    def __init__(self, lhs: ASTExpr, rhs: ASTExpr, op: TokenType) -> None:
        super().__init__(Span.merge(lhs.span, rhs.span))

        self.lhs = lhs
        self.rhs = rhs
        self.op = op

    def __repr__(self) -> str:
        return f'<BinaryOpExpr lhs={self.lhs!r} rhs={self.rhs!r} op={self.op!r}>'
    
class UnaryOpExpr(ASTExpr):
    def __init__(self, expr: ASTExpr, op: TokenType) -> None:
        super().__init__(expr.span)

        self.expr = expr
        self.op = op

    def __repr__(self) -> str:
        return f'<UnaryOpExpr expr={self.expr!r} op={self.op!r}>'
    
class DeleteExpr(ASTExpr):
    def __init__(self, expr: ASTExpr) -> None:
        super().__init__(expr.span)

        self.expr = expr

    def __repr__(self) -> str:
        return f'<DeleteExpr expr={self.expr!r}>'
    
class IdentifierExpr(ASTExpr):
    def __init__(self, span: Span, name: str) -> None:
        super().__init__(span)

        self.name = name

    def __repr__(self) -> str:
        return f'<IdentifierExpr name={self.name!r}>'
    
class VariableExpr(ASTExpr):
    def __init__(self, span: Span, name: str, value: ASTExpr, type: VariableType) -> None:
        super().__init__(span)

        self.name = name
        self.value = value
        self.type = type

    def __repr__(self) -> str:
        return f'<VariableExpr name={self.name!r} value={self.value!r} type={self.type!r}>'
    
class FunctionExpr(ASTExpr):
    def __init__(self, span: Span, name: str, args: List[str], body: Union[List[ASTExpr], ASTExpr]) -> None:
        super().__init__(span)

        self.name = name
        self.args = args
        self.body = body

    def __repr__(self) -> str:
        return f'<FunctionExpr name={self.name!r} args={self.args!r} body={self.body!r}>'
    
class ReturnExpr(ASTExpr):
    def __init__(self, value: ASTExpr) -> None:
        super().__init__(value.span)

        self.value = value

    def __repr__(self) -> str:
        return f'<ReturnExpr value={self.value!r}>'

class CallExpr(ASTExpr):
    def __init__(self, span: Span, callee: ASTExpr, args: List[ASTExpr]) -> None:
        super().__init__(span)

        self.callee = callee
        self.args = args

    def __repr__(self) -> str:
        return f'<CallExpr callee={self.callee!r} args={self.args!r}>'

class PreviousExpr(ASTExpr):
    def __init__(self, expr: ASTExpr) -> None:
        super().__init__(expr.span)

        self.expr = expr

    def __repr__(self) -> str:
        return f'<PreviousExpr expr={self.expr!r}>'
    
class AssertExpr(ASTExpr):
    def __init__(self, expr: ASTExpr, error: Optional[str] = None) -> None:
        super().__init__(expr.span)

        self.expr = expr
        self.error = error

    def __repr__(self) -> str:
        return f'<AssertExpr expr={self.expr!r}>'
    
class NewFileExpr(ASTExpr):
    def __init__(self, span: Span, filename: Optional[str]) -> None:
        super().__init__(span)

        self.filename = filename

    def __repr__(self) -> str:
        return f'<NewFileExpr filename={self.filename!r}>'
    
class ExportExpr(ASTExpr):
    def __init__(self, span: Span, symbol: str, to: str) -> None:
        super().__init__(span)

        self.symbol = symbol
        self.to = to

    def __repr__(self) -> str:
        return f'<ExportExpr symbol={self.symbol!r} to={self.to!r}>'
    
class ImportExpr(ASTExpr):
    def __init__(self, span: Span, symbol: str) -> None:
        super().__init__(span)

        self.symbol = symbol

    def __repr__(self) -> str:
        return f'<ImportExpr symbol={self.symbol!r}>'
    
class WhenExpr(ASTExpr):
    def __init__(self, span: Span, condition: ASTExpr, body: List[ASTExpr]) -> None:
        super().__init__(span)

        self.condition = condition
        self.body = body

    def __repr__(self) -> str:
        return f'<WhenExpr condition={self.condition!r} body={self.body!r}>'