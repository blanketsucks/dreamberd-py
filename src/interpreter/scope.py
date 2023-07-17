from __future__ import annotations

from typing import Optional, NamedTuple, TYPE_CHECKING, Dict, Any, List

from src.ast import ASTExpr, VariableType

if TYPE_CHECKING:
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

class Scope:
    def __init__(self, interpreter: Interpreter, parent: Optional[Scope] = None):
        self._interpreter = interpreter

        self.parent = parent
        self.variables: Dict[str, Variable] = {}

        self.return_value: Optional[Value[Any]] = None
    
    def set_return_value(self, value: Value[Any]) -> None:
        self.return_value = value

    def get_variable(self, name: str) -> Optional[Variable]:
        if name in self.variables:
            return self.variables[name]

        if self.parent is not None:
            return self.parent.get_variable(name)

        return None
    
    def __aenter__(self) -> Scope:
        return self
    
    def __aexit__(self, *args: Any) -> None:
        if self.parent:
            self._interpreter.scope = self.parent