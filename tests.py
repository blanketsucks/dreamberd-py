# Small script to test if the examples still compile after compiler changes

from __future__ import annotations

from typing import Iterable, List, Any, Tuple, Union, TypedDict

import os
import pathlib
import subprocess
import sys
import shlex
import json
import enum

# Colors because colors make everything better
class Colors(str, enum.Enum):
    Reset = '\033[0m'
    Red = '\033[1;31m'
    Green = '\033[1;32m'
    White = '\033[1;37m'

tests = pathlib.Path(__file__).parent / 'tests'
cwd = pathlib.Path(__file__).parent

def run(file: Union[str, os.PathLike[str]], args: Iterable[Any]) -> Tuple[int, str, str]:
    new = [sys.executable, '-m', 'src', str(file)]
    new.extend([shlex.quote(str(arg)) for arg in args])

    process = subprocess.Popen(new, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
    process.wait()

    assert process.stdout and process.stderr
    return process.returncode, process.stdout.read().decode(), process.stderr.read().decode()

class TestResult(TypedDict):
    returncode: int
    args: List[str]
    stdout: str
    stderr: str

class Test:
    def __init__(self, file: pathlib.Path) -> None:
        self.file = file

    def run(self) -> None:
        result = self.parse_output_file()
        returncode, stdout, stderr = run(self.file, result['args'])

        if returncode != result['returncode']:
            print(f'- {Colors.Red}Test {self.file} failed with return code {returncode}.{Colors.Reset}')
            print('    Expected return code:', result['returncode'])

            exit(1)

        if stdout != result['stdout']:
            print(f'- {Colors.Red}Test {self.file} failed.{Colors.Reset}')

            print('    Expected stdout:'); print(result['stdout'])
            print('    Actual stdout:'); print(stdout)

            exit(1)

        if stderr != result['stderr']:
            print(f'- {Colors.Red}Test {self.file} failed.{Colors.Red}')
            
            print('    Expected stderr:'); print(result['stderr'])
            print('    Actual stderr:'); print(stderr)

            exit(1)

    def update(self, *args: str) -> None:
        returncode, stdout, stderr = run(self.file, args)
        self.update_output_file(returncode, list(args), stdout, stderr)

    def has_output_file(self) -> bool:
        return self.file.with_suffix('.output.json').exists()

    def parse_output_file(self) -> TestResult:
        output = self.file.with_suffix('.output.json')
        with open(output, 'r') as f:
            return json.load(f)

    def update_output_file(
        self, returncode: int, args: List[str], stdout: str, stderr: str
    ) -> None:
        output = self.file.with_suffix('.output.json')
        with open(output, 'w') as f:
            json.dump({
                'returncode': returncode,
                'args': args,
                'stdout': stdout,
                'stderr': stderr
            }, f, indent=4)

def get(l: List[str], index: int, default: Any = None) -> Any:
    try:
        return l[index]
    except IndexError:
        return default

def main() -> None:
    do_update = (get(sys.argv, 1) == 'update')

    i = 0
    for file in tests.iterdir():
        if file.suffix != '.db':
            continue

        test = Test(file)
        print(f"-{Colors.White} Running test {i} ('{file}'){Colors.Reset}")

        if not test.has_output_file() or do_update:
            test.update()
            print('Updated output file.\n')

            i += 1
            continue

        test.run()
        i += 1

        print(f'- {Colors.Green}Passed.{Colors.Reset}\n')

    if do_update:
        action = 'updated'
    else:
        action = 'ran'

    print(f'\nSuccessfully {action} {i} tests.')

if __name__ == '__main__':
    main()