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
    args: List[Argument]
    body: List[ASTExpr]

    def call(self, args: List[Value[Any]], interpreter: Interpreter) -> Value[Any]:
        ...

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

def _print_single(value: Value[Any]) -> int:
    if value.type is ValueType.Array:
        fmt = '[{}]'
        return sys.stdout.write(fmt.format(', '.join([f'{element.value!r}' for element in value.value])))
    elif value.type is ValueType.Undefined:
        return sys.stdout.write('undefined')
    elif value.type is ValueType.Null:
        return sys.stdout.write('null')
    elif value.type is ValueType.Bool:
        if value.value is Bool.true:
            return sys.stdout.write('true')
        elif value.value is Bool.false:
            return sys.stdout.write('false')

        return sys.stdout.write('maybe')
    elif value.type is ValueType.Int:
        if isinstance(value.value, Array):
            return sys.stdout.write(str(value.value.to_int()))

        return sys.stdout.write(str(value.value))
    elif value.type is ValueType.String:
        return sys.stdout.write(value.value)

    return sys.stdout.write(str(value.value))

@register('print')
def _print(args: List[Value], interpreter: Interpreter) -> Value:
    for argument in args:
        _print_single(argument)

        sys.stdout.write(' ')
        
    sys.stdout.write('\n')
    sys.stdout.flush()

    return Value.undefined()
