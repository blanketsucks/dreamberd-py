from __future__ import annotations

from typing import Any, List, Dict, Optional, Tuple, TypeVar, Generic, TYPE_CHECKING
from enum import IntEnum, auto

if TYPE_CHECKING:
    from .scope import Variable

T = TypeVar('T')

class Bool(IntEnum): # One and a half bits
    false = 0
    true = 1
    maybe = 2

class ValueType(IntEnum):
    Int = auto()
    Float = auto()
    String = auto()
    Char = auto()
    Digit = auto()
    Bool = auto()
    Null = auto()
    Undefined = auto()
    Array = auto()
    Dict = auto()
    Object = auto()
    Function = auto()

class ArrayType(IntEnum):
    String = auto()
    Int = auto()
    Any = auto()

class Value(Generic[T]):
    def __init__(self, value: T, type: ValueType) -> None:
        self.value = value
        self.type = type

        self.ref: Optional[Variable] = None

    def __repr__(self) -> str:
        return f'<Value value={self.value!r} type={self.type!r}>'
    
    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Value):
            return False
        
        return self.value == other.value and self.type == other.type
    
    @classmethod
    def with_ref(cls, ref: Variable) -> Value[Any]:
        value = cls(ref.value.value, ref.value.type)
        value.ref = ref

        return value
        
    @classmethod
    def null(cls) -> Value:
        return Value(None, ValueType.Null) 

    @classmethod
    def undefined(cls) -> Value:
        return Value(None, ValueType.Undefined)
    
    @classmethod
    def true(cls) -> Value[Bool]:
        return Value(Bool.true, ValueType.Bool)
    
    @classmethod
    def false(cls) -> Value[Bool]:
        return Value(Bool.false, ValueType.Bool)
    
    @classmethod
    def maybe(cls) -> Value[Bool]:
        return Value(Bool.maybe, ValueType.Bool)

class Array:
    VALUE_TYPE_MAP: Dict[ArrayType, ValueType] = {
        ArrayType.String: ValueType.Char,
        ArrayType.Int: ValueType.Digit
    }

    def __init__(self, values: List[Value], type: ArrayType = ArrayType.Any) -> None:
        self.values: Dict[float, Value] = {i - 1: value for i, value in enumerate(values)}
        self.type = type

    def __repr__(self) -> str:
        return f'<Array length={self.length} type={self.type!r}>'

    def __len__(self) -> int:
        return self.length
    
    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Array):
            return False
        
        return self.values == other.values and self.type == other.type
    
    @property
    def length(self) -> int:
        return len(self.values)

    @classmethod
    def from_str(cls, string: str) -> Array:
        # TODO: Spec says strings are just arrays of chars
        return Array([Value(char, ValueType.String) for char in string], ArrayType.String)
    
    @classmethod
    def from_int(cls, integer: int) -> Array:
        # TODO: Spec says integers are just arrays of digits
        return Array([Value(int(digit), ValueType.Int) for digit in str(integer)], ArrayType.Int)
    
    def process(self, value: Value) -> Value:
        if self.type is ArrayType.Any:
            return value
        
        value.type = self.VALUE_TYPE_MAP[self.type]
        return value

    def pop(self, index: Optional[float] = None) -> Value:
        return self.values.pop(index if index else len(self.values) - 1)
    
    def push(self, value: Value) -> None:
        self.values[len(self.values)] = value

    def at(self, index: float) -> Value:
        value = self.values.get(index)
        if not value:
            return Value.undefined()
        
        return self.process(value)
    
    def insert(self, index: float, value: Value) -> None:
        self.values[index] = value

    def to_list(self) -> List[Value]:
        values: List[Value] = []
        for index in sorted(self.values.keys()):
            values.append(self.process(self.values[index]))

        return values
    
    def to_int(self) -> int:
        if self.type is not ArrayType.Int:
            return 0

        return int(''.join(str(value.value) for value in self.to_list()))
    
    def to_str(self) -> str:
        if self.type is not ArrayType.String:
            return ''

        return ''.join(str(value.value) for value in self.to_list())

class Dictionary:
    def __init__(self, values: List[Tuple[Value, Value]]) -> None:
        self.values: Dict[Any, Value[Any]] = {key.value: value for key, value in values}

    def __repr__(self) -> str:
        return f'<Dictionary length={self.length}>'
    
    def __len__(self) -> int:
        return self.length
    
    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Dictionary):
            return False
        
        return self.values == other.values
    
    @property
    def length(self) -> int:
        return len(self.values)
    
    def at(self, key: Value[Any]) -> Value[Any]:
        value = self.values.get(key.value)
        if not value:
            return Value.undefined()
        
        return value
    
    def insert(self, key: Value[Any], value: Value[Any]) -> None:
        self.values[key.value] = value

    def items(self):
        return self.values.items()

SPECIAL_VALUES = {
    "true": Value.true(),
    "false": Value.false(),
    "maybe": Value.maybe(),
    "null": Value.null(),
    "undefined": Value.undefined()
}