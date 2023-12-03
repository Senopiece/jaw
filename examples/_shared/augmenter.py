from dataclasses import dataclass
import re
import sys
from typing import Any, Callable, List


class Return:
    content: str

    def __init__(self, content: str):
        self.content = content

    @property
    def get(self) -> str:
        raise NotImplementedError()


@dataclass
class HexReturn(Return):
    def __init__(self, content: str):
        self.content = content

    @property
    def get(self):
        return "0x" + self.content


@dataclass
class BinReturn(Return):
    def __init__(self, content: str):
        self.content = content

    @property
    def get(self):
        return "0xb" + self.content


@dataclass
class XReportReturn(Return):
    def __init__(self, min: int, max: int | None):
        self.content = f"{hex(min)}-{hex(max) if max else 'inf'}"

    @property
    def get(self):
        return self.content


@dataclass
class Command:
    regex: re.Pattern[Any]
    func: Callable[..., Return]


commands: List[Command] = []
offset: int
r: int
m: int

registers_count: int
sizeofreg: int

nxs = re.compile(r"\{(N|X|S)\}")


def add_to_commands(pattern: str):
    def decorate(func: Callable[..., Return]) -> Callable[..., Return]:
        escaped_pattern = re.escape(pattern).replace("\\{", "{").replace("\\}", "}")
        regex_pattern = nxs.sub("(.*)", escaped_pattern)
        regex = re.compile(rf"^{regex_pattern}$")
        params: list[str] = nxs.findall(pattern)  # list[N/X/S]

        # {N} - dec/hex/bin number -> int
        # {X} - x or dec/hex/bin number -> int | None
        # {S} - any string -> str
        def mapargt(param, arg):
            match param:
                case "N":
                    return int(arg, base=0)
                case "X":
                    if arg == "x":
                        return None
                    return int(arg, base=0)
                case "S":
                    return arg
                case _:
                    raise ValueError()

        def wrapper(*args):
            cargs = []
            for param, arg in zip(params, args):
                cargs.append(mapargt(param, arg))
            return func(*cargs)

        commands.append(
            Command(
                regex=regex,
                func=wrapper,
            )
        )

        return func

    return decorate


def mb(n: int, size: int):
    if n >= 2**size:
        raise ValueError(f"Value of {n} cannot fit into {size} bits.")
    return f"{n:0{size}b}"


# # Basic instructions
@add_to_commands("mem[reg{N}] = {N}")
def set_mem_bit(n: int, b: int):
    # 00{n:[r bits]}{<0/1>:[1 bit]}
    return BinReturn(f"00{mb(n, r)}{mb(b, 1)}")


@add_to_commands("mem[reg{N}] ? pp += reg{N}")
def cnd_jmp_mem(n: int, k: int):
    # 01{n:[r bits]}{k:[r bits]}
    return BinReturn(f"01{mb(n, r)}{mb(k, r)}")


@add_to_commands("reg[{N}][{N}] = {N}")
def set_reg_bit(n: int, i: int, b: int):
    # 10{n:[r bits]}{i:[m bits]}{<0/1>:[1 bit]}
    return BinReturn(f"10{mb(n, r)}{mb(i, m)}{mb(b, 1)}")


@add_to_commands("reg{N}[{N}] ? pp += reg{N}")
def cnd_jmp_reg(n: int, i: int, k: int):
    # 11{n:[r bits]}{i:[m bits]}{k:[r bits]}
    return BinReturn(f"11{mb(n, r)}{mb(i, m)}{mb(k, r)}")


# # Complex instructions
@add_to_commands("reg{N}: {S} = const {X}")
def set_full_reg_with_const(n: int, init: str, const: int | None):
    if init == "x" or const is None:
        return XReportReturn(0, sizeofreg * len(set_reg_bit(0, 0, 0).content))

    if init == "any":
        return BinReturn(set_full_reg_from_any(n, const))

    return BinReturn(set_full_reg_from_known(n, int(init, base=0), const))


def set_full_reg_from_known(n: int, init: int, const: int):
    res = ""
    for i, wasbit, needbit in zip(
        range(sizeofreg), mb(init, sizeofreg), mb(const, sizeofreg)
    ):
        if wasbit != needbit:
            res += set_reg_bit(n, i, int(needbit)).content
    return res


def set_full_reg_from_any(n: int, const: int):
    return "".join(
        set_reg_bit(n, i, int(bit)).content
        for i, bit in enumerate(mb(const, sizeofreg))
    )


@add_to_commands("reg{N}: {S} = const {X} - {X}")
def set_full_reg_with_const_diff(n: int, init: str, a: int | None, b: int | None):
    if a is None or b is None:
        return XReportReturn(0, sizeofreg * len(set_reg_bit(0, 0, 0).content))
    return set_full_reg_with_const(n, init, a - b)


# TODO: regN == X ? pp = X
# TODO: regN[N] = mem[regN]
# TODO: regN++


@add_to_commands('#store_unicode "{S}"')
def store_unicode(s: str):
    s = s.encode().decode("unicode-escape")
    res = ""
    for ch in s:
        res += f"{ord(ch):04x}"
    return HexReturn(res)


@add_to_commands('#dumb_stdout "{S}"')
def dumb_stdout(s: str):
    # assumes reg0 is set to 0x0, reg1 is set to 0x1, reg2 is set to 0x2
    s = s.encode().decode("unicode-escape")
    res = ""
    for ch in s:
        for bit in f"{ord(ch):016b}":
            res += set_mem_bit(1, int(bit)).content  # mem[reg1] = bit // set data
            res += set_mem_bit(2, 1).content  # mem[reg2] = 1 // trigger collect
    res += set_mem_bit(0, 1).content  # mem[reg0] = 1 // halt
    return BinReturn(res)


if __name__ == "__main__":
    _, _offset, _r, _m, msg = sys.argv
    offset = int(_offset, base=16)  # use for computation of labels
    r = int(_r)
    m = int(_m)

    registers_count = 2**r
    sizeofreg = 2**m

    for cmd in commands:
        res = cmd.regex.search(msg)
        if res is None:
            continue
        print(cmd.func(*res.groups()).get)
        break
    else:
        raise ValueError(msg)
