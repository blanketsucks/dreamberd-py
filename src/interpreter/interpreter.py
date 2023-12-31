from typing import Set, Union, Any, Optional, cast, Dict, List

from src.ast import *
from src.tokens import TokenType, Span
from src.errors import error
from src.ast.parser import EQ_TYPES, NEQ_TYPES_TO_EQ

from .value import SPECIAL_VALUES, Bool, Dictionary, Value, ValueType, Array
from .scope import ClassInstance, Scope, Variable, WhenMutated, Class
from .function import Function, ALL_BUILTINS, Coroutine

# TODO: The spec says that integers are just an array of digits so in theory it should be possible to have
# ```
# var var num = 1234!
# num.pop()!
# print(num)! # 123
# ```

INTEGER_TYPES = (ValueType.Int, ValueType.Digit, ValueType.Float)

class Interpreter:
    def __init__(self, filename: str, ast: List[ASTExpr]) -> None:
        self.ast = ast

        self.scope = Scope(self)
        self.filename = filename

        self.files: Dict[str, Scope] = {}
        self.exports: Dict[str, Dict[str, Any]] = {}

        self.deleted_values: Set[Value] = set()

        self.coroutines: List[Coroutine] = []

    def finalize(self) -> None:
        while self.coroutines:
            self.execute_pending_coroutines()

    def is_deleted_value(self, value: Value) -> bool:
        for val in self.deleted_values:
            if val.value == value.value and val.type == value.type:
                return True
            
        return False

    def export_symbol(self, symbol: Any, name: str, to: str) -> None:
        exports = self.exports.setdefault(to, {})
        exports[name] = symbol

    def validate(self, span: Span, value: Value[Any]) -> Value[Any]:
        if self.is_deleted_value(value):
            error(span, f'{value.value} has been deleted')

        return value
    
    def cmp(self, lhs: Value[Any], op: TokenType, rhs: Value[Any]) -> Bool:
        if op in (TokenType.Assign, TokenType.Eq): # I don't know what's the difference between = and ==
            # Lowest precision comparasion
            if lhs.type is not rhs.type:
                rhs.value = type(lhs.value)(rhs.value) # A bit hacky but whatever

            result = Bool(lhs.value == rhs.value)
        elif op is TokenType.TripleEq:
            if lhs.type is not rhs.type:
                result = Bool.false
            else:
                result = Bool(lhs.value == rhs.value)
        else:
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

        return result
    
    def add_coroutine(self, coroutine: Coroutine) -> None:
        self.coroutines.append(coroutine)

    def execute_pending_coroutines(self) -> None:
        for coroutine in self.coroutines.copy():
            if coroutine.skip_current_newline:
                coroutine.skip_current_newline = False
                continue

            if coroutine.body:
                pending = coroutine.body.pop(0)
                if isinstance(pending, StringExpr):
                    continue
                elif isinstance(pending, ReturnExpr):
                    value = self.visit(pending.value)
                    coroutine.set_result(value)

                    coroutine.body = [] # Basically cancel the coroutine
                    self.coroutines.remove(coroutine)

                    continue

                self.visit(pending)

    def visit(self, expr: ASTExpr) -> Value[Any]:
        if isinstance(expr, NewlineExpr):
            self.execute_pending_coroutines()
            return Value.undefined()

        method = getattr(self, f'visit_{expr.__class__.__name__}')
        return self.validate(expr.span, method(expr))
    
    def visit_ReverseExpr(self, expr: ReverseExpr) -> Value[Any]:
        ast = self.ast.copy()
        ast.remove(expr)

        ast.reverse()

        for coroutine in self.coroutines:
            coroutine.body.reverse()

        self.scope = Scope(self)
        for stmt in ast:
            self.visit(stmt)

        return Value.undefined()

    def visit_IntegerExpr(self, expr: IntegerExpr) -> Value[int]:
        if str(expr.value) in self.scope.variables:
            variable = self.scope.variables[str(expr.value)]
            return Value.with_ref(variable)

        return Value(expr.value, ValueType.Int)

    def visit_StringExpr(self, expr: StringExpr) -> Value[str]:
        return Value(expr.value, ValueType.String)
    
    def visit_ArrayExpr(self, expr: ArrayExpr) -> Value[Array]:
        return Value(Array([self.visit(value) for value in expr.values]), ValueType.Array)
    
    def visit_DictExpr(self, expr: DictExpr) -> Value[Dictionary]:
        values = [
            (self.visit(key), self.visit(value)) for key, value in expr.values
        ]

        for key, _ in values:
            if key.type not in (ValueType.Int, ValueType.Digit, ValueType.String):
                # This is a python limitation as any other type is not hashable and cannot be put into a dictionary
                error(expr.span, 'Dictionary key must be an integer, digit or string')

        return Value(Dictionary(values), ValueType.Dict)
    
    def visit_IndexExpr(self, expr: IndexExpr) -> Value[Any]:
        value: Value[Union[Array, Dictionary, int, str]] = self.visit(expr.value)
        index: Value[Union[int, float]] = self.visit(expr.index)

        # Because Int == Digit[], `123[0]` should be possible
        if value.type not in (ValueType.Array, ValueType.String, ValueType.Int, ValueType.Dict):
            error(expr.value.span, 'Cannot index value')

        if isinstance(value.value, Dictionary):
            return value.value.at(index)

        if index.type not in (ValueType.Int, ValueType.Digit, ValueType.Float):
            error(expr.index.span, 'Cannot index with non-integer value')

        arr: Value[Union[Array, int, str]] = value # type: ignore
        if isinstance(arr.value, int):
            arr.value = Array.from_int(arr.value)
        elif isinstance(arr.value, str):
            arr.value = Array.from_str(arr.value)

        idx = index.value
        if idx < -len(arr.value) or idx >= len(arr.value):
            error(expr.index.span, f'Array index out of bounds')

        return arr.value.at(idx)
        
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
        coroutine: Optional[Coroutine] = None

        if value.type is ValueType.Coroutine:
            coroutine = value.value
            value = value.value.result or Value.undefined()

        variable = Variable(expr.name, value, expr.extras['boldness'], expr.type)
        if coroutine:
            coroutine.store = variable

        self.scope.variables[expr.name] = variable
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
        
        if expr.name in SPECIAL_VALUES:
            return SPECIAL_VALUES[expr.name]

        # The spec says that `const const name = Luke!` here Luke should be a string
        return Value(expr.name, ValueType.String)
    
    def visit_FunctionExpr(self, expr: FunctionExpr) -> Value[Any]:
        is_single_expr = not isinstance(expr.body, list)
        body = expr.body if isinstance(expr.body, list) else [expr.body]

        function = Function(expr.name, expr.args, body, is_single_expr, expr.is_async)
        self.scope.functions[expr.name] = function

        return Value(function, ValueType.Function)
    
    def visit_ReturnExpr(self, expr: ReturnExpr) -> Value[Any]:
        value = self.visit(expr.value)
        self.scope.set_return_value(value)

        return Value.undefined()

    def visit_BinaryOpExpr(self, expr: BinaryOpExpr) -> Value:
        if isinstance(expr.lhs, IndexExpr) and expr.op is TokenType.Assign:
            index = self.visit(expr.lhs.index)
            parent = self.visit(expr.lhs.value)

            if parent.type not in (ValueType.Array, ValueType.Dict):
                error(expr.lhs.value.span, 'Cannot index value')

            if isinstance(parent.value, Dictionary):
                if index.type not in (ValueType.Int, ValueType.Digit, ValueType.String):
                    error(expr.lhs.index.span, 'Dictionary key must be an integer, digit or string')

                parent.value.insert(index, self.visit(expr.rhs))
                return Value.undefined()

            if index.type not in (ValueType.Int, ValueType.Digit, ValueType.Float):
                error(expr.lhs.index.span, 'Array index must be an integer, digit or float')

            parent.value.insert(index.value, self.visit(expr.rhs))
            return Value.undefined()    
        
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
        elif expr.op in EQ_TYPES:
            result = self.cmp(lhs, expr.op, rhs)
            ty = ValueType.Bool
        elif expr.op in (TokenType.NAssign, TokenType.NEq, TokenType.NTripleEq, TokenType.NQuadEq):
            result = Bool(not self.cmp(lhs, NEQ_TYPES_TO_EQ[expr.op], rhs).value)
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
        self.finalize()
        self.scope = Scope(self) # TODO: This is how it is for now but it might change

        if expr.filename:
            self.filename = expr.filename
            self.files[expr.filename] = self.scope

        return Value.undefined()
    
    def visit_ExportExpr(self, expr: ExportExpr) -> Value[Any]:
        symbol = self.scope.get_variable(expr.symbol)
        if symbol:
            self.export_symbol(symbol, expr.symbol, expr.to)
            return Value.undefined()
        
        symbol = self.scope.get_function(expr.symbol)
        if symbol:
            self.export_symbol(symbol, expr.symbol, expr.to)
            return Value.undefined()
        
        symbol = self.scope.get_class(expr.symbol)
        if symbol:
            self.export_symbol(symbol, expr.symbol, expr.to)
            return Value.undefined()

        error(expr.span, 'Cannot export non-existent symbol')
    
    def visit_ImportExpr(self, expr: ImportExpr) -> Value[Any]:
        exports = self.exports.get(self.filename, {})
        if expr.symbol not in exports:
            error(expr.span, 'Cannot import non-existent symbol')

        export = exports[expr.symbol]
        if isinstance(export, Variable):
            self.scope.variables[export.name] = export
        elif isinstance(export, Function):
            self.scope.functions[export.name] = export
        elif isinstance(export, Class):
            self.scope.classes[export.name] = export
        
        return Value.undefined()

    def visit_WhenExpr(self, expr: WhenExpr) -> Value[Any]:
        cond = cast(BinaryOpExpr, expr.condition)
        value = self.visit(cond.lhs)

        if not value.ref:
            error(cond.lhs.span, 'When condition must be a variable')

        value.ref.when_mutated = WhenMutated(cond, expr.body)
        return Value.undefined()

    def visit_AwaitExpr(self, expr: AwaitExpr) -> Value[Any]:
        if not isinstance(expr.expr, CallExpr):
            error(expr.span, 'Can only await function calls')

        call = cast(CallExpr, expr.expr)
        callee: Value[Function] = self.visit(call.callee)

        if callee.type is not ValueType.Function:
            error(call.callee.span, 'Can only await function calls')

        if not callee.value.is_async:
            error(call.callee.span, 'Can only await async functions')

        return callee.value.call([self.visit(arg) for arg in call.args], self, await_result=True)
    
    def visit_ClassExpr(self, expr: ClassExpr) -> Value[Any]:
        scope = Scope(self, self.scope)
        with scope:
            for stmt in expr.body:
                self.visit(stmt)

        self.scope.classes[expr.name] = Class(expr.name, scope)
        return Value.undefined()
    
    def visit_NewExpr(self, expr: NewExpr) -> Value[Any]:
        cls = self.scope.get_class(expr.name)
        if not cls:
            error(expr.span, 'Cannot instantiate non-existent class')

        if cls.has_instance:
            error(expr.span, f'Can\'t have more than one {cls.name!r} instance!')

        instance = ClassInstance(cls)
        cls.has_instance = True

        # The spec says nothing about `self` or `this` so I don't know if i should add it or not
        return Value(instance, ValueType.Object)
    
    def visit_AttributeExpr(self, expr: AttributeExpr) -> Value[Any]:
        value: Value[ClassInstance] = self.visit(expr.value)
        if value.type is not ValueType.Object:
            error(expr.value.span, 'Cannot access attribute of non-object value')

        instance = value.value
        return instance.getattr(expr.attribute)