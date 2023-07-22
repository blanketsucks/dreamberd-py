from __future__ import annotations

from typing import Optional, NamedTuple, TYPE_CHECKING, Dict, Any, List

from src.ast import ASTExpr, VariableType

if TYPE_CHECKING:
    from .function import Function
    from .interpreter import Interpreter
    from .value import Value

class WhenMutated(NamedTuple):
    condition: ASTExpr
    body: List[ASTExpr]

class Variable:
    def __init__(
        self, name: str, value: Value[Any], boldness: int, type: VariableType
    ) -> None:
        self.name = name
        self.value = value
        self.boldness = boldness
        self.type = type

        self.previous = value

        self.when_mutated: Optional[WhenMutated] = None

class Class:
    def __init__(self, name: str, scope: Scope) -> None:
        self.name = name
        self.scope = scope
        self.has_instance = False

class ClassInstance:
    def __init__(self, cls: Class) -> None:
        self.cls = cls

    def getattr(self, name: str) -> Value[Any]:
        from .value import Value, ValueType

        attr = self.cls.scope.get_variable(name)
        if attr:
            return Value.with_ref(attr)
        
        attr = self.cls.scope.get_function(name)
        if attr:
            return Value(attr, ValueType.Function)
        
        return Value.undefined()

class Scope:
    def __init__(self, interpreter: Interpreter, parent: Optional[Scope] = None):
        self._interpreter = interpreter

        self.parent = parent

        self.variables: Dict[str, Variable] = {}
        self.functions: Dict[str, Function] = {}
        self.classes: Dict[str, Class] = {}

        self.return_value: Optional[Value[Any]] = None
    
    def set_return_value(self, value: Value[Any]) -> None:
        self.return_value = value

    def get_variable(self, name: str) -> Optional[Variable]:
        if name in self.variables:
            return self.variables[name]

        if self.parent is not None:
            return self.parent.get_variable(name)

        return None
    
    def get_function(self, name: str) -> Optional[Function]:
        if name in self.functions:
            return self.functions[name]

        if self.parent is not None:
            return self.parent.get_function(name)

        return None
    
    def get_class(self, name: str) -> Optional[Class]:
        if name in self.classes:
            return self.classes[name]

        if self.parent is not None:
            return self.parent.get_class(name)

        return None
    
    def __enter__(self) -> Scope:
        return self
    
    def __exit__(self, *args: Any) -> None:
        if self.parent:
            self._interpreter.scope = self.parent