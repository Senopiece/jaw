import sys
from typing import Callable, Dict

commands: Dict[str, Callable[..., str]] = {}
offset: int
r: int
m: int

registers_count: int
sizeofreg: int

def add_to_commands(func: Callable[..., str]) -> Callable[..., str]:
    commands[func.__name__] = func
    return func

@add_to_commands
def setall(reg: str, value: str):
    res = ""
    for i in range(sizeofreg):
        res += f"{reg}[0xb{i:04b}] = {value}\n"
    return res

@add_to_commands
def store_unicode(s: str):
    res = ">0x"
    for ch in s:
        res += f"{ord(ch):04x}"
    return res

if __name__ == "__main__":
    _, command, _offset, _r, _m, *args  = sys.argv
    offset = int(_offset, base=16) # use for computation of labels
    r = int(_r)
    m = int(_m)

    registers_count = 2**r
    sizeofreg = 2**m

    print(commands[command](*args))