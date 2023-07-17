from __future__ import annotations

from typing import NamedTuple, List, TYPE_CHECKING, Dict, Callable, Any
import sys

from src.ast import ASTExpr
from .value import Value, ValueType, Bool, Array

if TYPE_CHECKING:
    from .interpreter import Interpreter

ALL_BUILTINS: Dict[str, BuiltinFunction] = {}

class Argument(NamedTuple):
    name: str

class Function(NamedTuple):
    name: str
    args: List[str]
    body: List[ASTExpr]
    is_single_expr: bool

    def call(self, args: List[Value[Any]], interpreter: Interpreter) -> Value[Any]:
        from .scope import Scope, Variable, VariableType

        scope = Scope(interpreter, interpreter.scope)
        interpreter.scope = scope

        with scope:
            for index, argument in enumerate(self.args):
                scope.variables[argument] = Variable(
                    argument, args[index], 0, VariableType.VarVar
                )

            if self.is_single_expr:
                scope.return_value = interpreter.visit(self.body[0])
            else:
                for expr in self.body:
                    interpreter.visit(expr)

                    if scope.return_value:
                        break

        return scope.return_value or Value.undefined()

class BuiltinFunction(NamedTuple):
    name: str
    args: List[Argument]
    callable: Callable[[List[Value[Any]], Interpreter], Value[Any]]

    def call(self, args: List[Value[Any]], interpreter: Interpreter) -> Value:
        return self.callable(args, interpreter)
    
def register(name: str):
    def decorator(func: Callable[[List[Value[Any]], Interpreter], Value[Any]]):
        ALL_BUILTINS[name] = BuiltinFunction(name, [], func)
        return func
    return decorator

def format_value(value: Value[Any]) -> Any:
    if value.type is ValueType.Array:
        fmt = '['
        for elem in value.value:
            is_last = elem is value.value[-1]
            
            fmt += format_value(elem)
            if not is_last:
                fmt += ', '

        fmt += ']'
    elif value.type is ValueType.Dict:
        fmt = '{'
        for i, (key, val) in enumerate(value.value.items()):
            is_last = i == len(value.value) - 1
            fmt += f'{key!r}: {format_value(val)!r}'

            if not is_last:
                fmt += ', '

        fmt += '}'
    elif value.type is ValueType.Undefined:
        fmt = 'undefined'
    elif value.type is ValueType.Null:
        fmt = 'null'
    elif value.type is ValueType.Bool:
        if value.value is Bool.true:
            fmt = 'true'
        elif value.value is Bool.false:
            fmt = 'false'
        else:
            fmt = 'maybe'
    else:
        fmt = value.value

    return fmt

@register('print')
def _print(args: List[Value], _: Interpreter) -> Value:
    for argument in args:
        sys.stdout.write(str(format_value(argument)))
        sys.stdout.write(' ')
        
    sys.stdout.write('\n')
    sys.stdout.flush()

    return Value.undefined()
