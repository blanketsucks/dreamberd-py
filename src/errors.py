from typing import NoReturn

from enum import Enum
import sys

from .tokens import Span

class Colors(str, Enum):
    Reset = '\033[0m'
    Red = '\033[1;31m'
    White = '\033[1;37m'

def error(span: Span, message: str) -> NoReturn:
    sys.stdout.write(f'{Colors.White}{span.filename}:{span.start.line}:{span.start.column}{Colors.Reset}')
    sys.stdout.write(f' {Colors.Red}Error:{Colors.Reset} {message}\n')

    sys.stdout.write(f'{Colors.White}{span.start.line} |{Colors.Reset} {span.line}\n')
    sys.stdout.flush()

    sys.exit(1)