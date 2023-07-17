import sys

from .lexer import Lexer
from .ast import Parser
from .interpreter import Interpreter

def main() -> None:
    if len(sys.argv) != 2:
        print(f'No file specified')
        sys.exit(1)

    with open(sys.argv[1], 'r', encoding='utf-8') as file:
        source = file.read()

    lexer = Lexer(source.strip(), sys.argv[1])
    tokens = list(lexer)

    parser = Parser(tokens)
    ast = parser.parse()

    interpreter = Interpreter(sys.argv[1], ast)
    for stmt in ast:
        interpreter.visit(stmt)

if __name__ == '__main__':
    main()