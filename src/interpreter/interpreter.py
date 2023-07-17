from typing import Set, Union, Any, Optional, cast, Dict, List

from src.ast import *
from src.tokens import TokenType, Span
from src.errors import error

from .value import Bool, Value, ValueType, Array
from .scope import Scope, Variable, WhenMutated
from .function import Function, ALL_BUILTINS

# TODO: The spec says that integers are just an array of digits so in theory it should be possible to have
# ```
# var var num = 1234!
# num.pop()!
# print(num)! # 123
# ```

INTEGER_TYPES = (ValueType.Int, ValueType.Digit, ValueType.Float)

class Interpreter:
    def __init__(self, filename: str) -> None:
        self.scope = Scope(self)
        self.filename = filename

        self.files: Dict[str, Scope] = {}
        self.exports: Dict[str, Dict[str, Any]] = {}

        self.deleted_values: Set[Value] = set()

    def is_deleted_value(self, value: Value) -> bool:
        for val in self.deleted_values:
            if val.value == value.value and val.type == value.type:
                return True
            
        return False

    def validate(self, span: Span, value: Value[Any]) -> Value[Any]:
        if self.is_deleted_value(value):
            error(span, f'{value.value} has been deleted')

        return value

    def visit(self, expr: ASTExpr) -> Value[Any]:
        # A bit cursed but whatever
        method = getattr(self, f'visit_{expr.__class__.__name__}') 
        return self.validate(expr.span, method(expr))

    def visit_IntegerExpr(self, expr: IntegerExpr) -> Value[int]:
        if str(expr.value) in self.scope.variables:
            variable = self.scope.variables[str(expr.value)]
            return Value.with_ref(variable)

        return Value(expr.value, ValueType.Int)

    def visit_StringExpr(self, expr: StringExpr) -> Value[str]:
        return Value(expr.value, ValueType.String)
    
    def visit_ArrayExpr(self, expr: ArrayExpr) -> Value[Array]:
        return Value(Array([self.visit(value) for value in expr.values]), ValueType.Array)
    
    def visit_ArrayIndexExpr(self, expr: ArrayIndexExpr) -> Value[Any]:
        array: Value[Union[Array, int, str]] = self.visit(expr.array)
        index: Value[Union[int, float]] = self.visit(expr.index)

        # Because Int == Digit[], `123[0]` should be possible
        if array.type not in (ValueType.Array, ValueType.String, ValueType.Int):
            error(expr.array.span, 'Cannot index non-array value')

        if index.type not in (ValueType.Int, ValueType.Digit, ValueType.Float):
            error(expr.index.span, 'Cannot index with non-integer value')

        if isinstance(array.value, int):
            array.value = Array.from_int(array.value)
        elif isinstance(array.value, str):
            array.value = Array.from_str(array.value)

        idx = index.value
        if idx < -len(array.value) or idx >= len(array.value):
            error(expr.index.span, f'Array index out of bounds')

        return array.value.at(idx)
    
    def visit_CallExpr(self, expr: CallExpr) -> Value[Any]:
        callee: Value[Function] = self.visit(expr.callee)
        if callee.type is not ValueType.Function:
            error(expr.callee.span, 'Cannot call non-function value')

        args = [self.visit(arg) for arg in expr.args]
        return callee.value.call(args, self)
    
    def visit_DeleteExpr(self, expr: DeleteExpr) -> Value[Any]:
        value = self.visit(expr.expr)
        self.deleted_values.add(value)

        return Value.undefined()
    
    def visit_VariableExpr(self, expr: VariableExpr) -> Value[Any]:
        variable = self.scope.get_variable(expr.name)
        if variable and variable.boldness > expr.extras['boldness']:
            return Value.undefined()
        
        value = self.visit(expr.value)
        self.scope.variables[expr.name] = Variable(expr.name, value, expr.extras['boldness'], expr.type)
            
        return Value.undefined()
    
    def visit_IdentifierExpr(self, expr: IdentifierExpr) -> Value[Any]:
        variable = self.scope.get_variable(expr.name)
        if variable:
            return Value.with_ref(variable)
        
        function = self.scope.get_function(expr.name)
        if function:
            return Value(function, ValueType.Function)
        
        if expr.name in ALL_BUILTINS:
            return Value(ALL_BUILTINS[expr.name], ValueType.Function)

        # The spec says that `const const name = Luke!` here Luke should be a string
        return Value(expr.name, ValueType.String)
    
    def visit_FunctionExpr(self, expr: FunctionExpr) -> Value[Any]:
        is_single_expr = not isinstance(expr.body, list)
        body = expr.body if isinstance(expr.body, list) else [expr.body]

        self.scope.functions[expr.name] = Function(expr.name, expr.args, body, is_single_expr)
        return Value.undefined()
    
    def visit_ReturnExpr(self, expr: ReturnExpr) -> Value[Any]:
        value = self.visit(expr.value)
        self.scope.set_return_value(value)

        return Value.undefined()

    def visit_BinaryOpExpr(self, expr: BinaryOpExpr) -> Value:
        lhs, rhs = self.visit(expr.lhs), self.visit(expr.rhs)

        if lhs.ref and expr.op is TokenType.Assign:
            if lhs.ref.type in (VariableType.ConstConst, VariableType.ConstConstConst, VariableType.ConstVar):
                error(expr.lhs.span, 'Cannot assign to const variable')

            lhs.ref.previous = lhs.ref.value
            lhs.ref.value = rhs

            if lhs.ref.when_mutated:
                self.scope = Scope(self, self.scope)
                for stmt in lhs.ref.when_mutated.body:
                    self.visit(stmt)

                self.scope: Scope = self.scope.parent # type: ignore

            return Value.undefined()
        
        ty: Optional[ValueType] = None
        if expr.op is TokenType.Plus:
            if lhs.type not in INTEGER_TYPES or rhs.type not in INTEGER_TYPES:
                error(expr.lhs.span, 'Cannot add non-integer value')

            result = lhs.value + rhs.value
        elif expr.op is TokenType.Minus:
            if lhs.type not in INTEGER_TYPES or rhs.type not in INTEGER_TYPES:
                error(expr.lhs.span, 'Cannot substract non-integer value')

            result = lhs.value - rhs.value
        elif expr.op is TokenType.Mul:
            if lhs.type not in INTEGER_TYPES or rhs.type not in INTEGER_TYPES:
                error(expr.lhs.span, 'Cannot multiply non-integer value')

            result = lhs.value * rhs.value
        elif expr.op is TokenType.Div:
            if lhs.type not in INTEGER_TYPES or rhs.type not in INTEGER_TYPES:
                error(expr.lhs.span, 'Cannot divide non-integer value')

            if rhs.value == 0:
                return Value.undefined()

            result = lhs.value // rhs.value
        elif expr.op in (TokenType.Assign, TokenType.Eq): # I don't know what's the difference between = and ==
            # Lowest precision comparasion
            if lhs.type is not rhs.type:
                rhs.value = type(lhs.value)(rhs.value) # A bit hacky but whatever

            result = Bool(lhs.value == rhs.value)
            ty = ValueType.Bool
        elif expr.op is TokenType.TripleEq:
            if lhs.type is not rhs.type:
                result = Bool.false
            else:
                result = Bool(lhs.value == rhs.value)
            
            ty = ValueType.Bool
        elif expr.op is TokenType.QuadEq:
            if lhs.ref:
                if not rhs.ref:
                    result = Bool.false
                else:
                    result = Bool(lhs.ref is rhs.ref)
            else:
                if lhs.type is not rhs.type:
                    result = Bool.false
                else:
                    result = Bool(lhs.value == rhs.value)

            ty = ValueType.Bool
        else:
            raise RuntimeError(f'Unknown binary operator {expr.op!r}')
        
        return Value(result, ty or lhs.type)
    
    def visit_UnaryOpExpr(self, expr: UnaryOpExpr) -> Value:
        value = self.visit(expr.expr)
        if value.type not in (ValueType.Int, ValueType.Digit, ValueType.Float, ValueType.Bool):
            error(expr.expr.span, 'Cannot use unary operator on non-integer value')

        if expr.op is TokenType.SemiColon:
            return Value(not value.value, ValueType.Bool)
        elif expr.op is TokenType.Minus:
            return Value(-value.value, ValueType.Int)

        raise RuntimeError(f'Unknown unary operator {expr.op!r}')
    
    def visit_PreviousExpr(self, expr: PreviousExpr) -> Value[Any]:
        value = self.visit(expr.expr)
        if not value.ref:
            return Value.undefined()
        
        return value.ref.previous
    
    def visit_AssertExpr(self, expr: AssertExpr) -> Value[Any]:
        value = self.visit(expr.expr)
        if not value.value:
            if expr.error:
                error(expr.span, f'Assertion failed. {expr.error}')

            error(expr.span, 'Assertion failed')

        return Value.undefined()
    
    def visit_NewFileExpr(self, expr: NewFileExpr) -> Value[Any]:
        self.scope = Scope(self) # TODO: This is how it is for now but it might change
        if expr.filename:
            self.filename = expr.filename
            self.files[expr.filename] = self.scope

        return Value.undefined()
    
    def visit_ExportExpr(self, expr: ExportExpr) -> Value[Any]:
        symbol = self.scope.get_variable(expr.symbol)
        if not symbol:
            symbol = self.scope.get_function(expr.symbol)
            if not symbol:
                error(expr.span, 'Cannot export non-existent symbol')

        exports = self.exports.setdefault(expr.to, {})
        exports[expr.symbol] = symbol

        return Value.undefined()
    
    def visit_ImportExpr(self, expr: ImportExpr) -> Value[Any]:
        exports = self.exports.get(self.filename, {})
        if expr.symbol not in exports:
            error(expr.span, 'Cannot import non-existent symbol')

        export = exports[expr.symbol]
        if isinstance(export, Variable):
            self.scope.variables[export.name] = export
        elif isinstance(export, Function):
            self.scope.functions[export.name] = export
        
        return Value.undefined()

    def visit_WhenExpr(self, expr: WhenExpr) -> Value[Any]:
        cond = cast(BinaryOpExpr, expr.condition)
        if not isinstance(cond.lhs, IdentifierExpr):
            error(cond.lhs.span, 'When condition must be a variable')

        variable = self.scope.get_variable(cond.lhs.name)
        if not variable:
            error(cond.lhs.span, 'When condition must be a variable')

        variable.when_mutated = WhenMutated(cond, expr.body)
        return Value.undefined()
