# this vm is emulating jaw machine with the following arch and evnirionment:

# arch: register number and address space are parametrized
# >? the name for the arch: jaw-{r}x{m}

# envirionment `a`:

# special memory addresses:
# - 0x0: when 1 is written, the program halts
# - 0x1: stdout signal
# - 0x2: stdout trigger (reading value from there produces undefined result) (when 1 is written, writes stdout signal to the buffer, when buffer reaches 8 bits, it is printed as ascii character)
# - 0x3-0xx: the place where your program is located

# valid assumptions:
# - at the start of the program all the memory except for the `special memory addresses`` is filled with zeroes
# - at the start of the program all registers are filled with zeroes
# - the program pointer starts from 0x3

# the fullname of the context is `{arch}:{env}` = `jaw-{r}x{m}:a`

import argparse
import sys
from typing import List


def b2i(bits: List[bool]) -> int:
    return int("".join(["1" if b else "0" for b in bits]), 2)


class BitStdOut:
    _buf: List[bool]

    def __init__(self) -> None:
        self._buf = []

    def fwd(self, b: bool):
        self._buf.append(b)
        if len(self._buf) == 8:
            sys.stdout.write(chr(b2i(self._buf)))
            self._buf = []


def exec_jaw(debug: bool, r: int, m: int, program: str):
    CODE_BEGINNING = 3

    if r < 1:
        print("Error: Register space must be greater than or equal to 1.")
        return
    if m < 1:
        print("Error: Address space must be greater than or equal to 1.")
        return

    sizeofreg = 2**m
    registers_count = 2**r

    mem: List[bool] = [False] * 2**sizeofreg
    sizeofmem = 2**sizeofreg

    with open(program, "rb") as f:
        byte = f.read(1)
        pos = CODE_BEGINNING
        while byte:
            for bit in format(int.from_bytes(byte, "big"), "08b"):
                mem[pos] = bit == "1"
                pos += 1
            byte = f.read(1)

    pos = CODE_BEGINNING
    registers: List[List[bool]] = [[False] * sizeofreg for _ in range(registers_count)]

    def memread_1bit():
        nonlocal pos
        res = mem[pos]
        pos = (1 + pos) % sizeofmem
        return res

    def memread(bits: int):
        return [memread_1bit() for _ in range(bits)]

    stdout = BitStdOut()

    # 00{n:[r bits]}{<0/1>:[1 bit]}              = mem[reg[n]] = <0/1>
    # 01{n:[r bits]}{k:[r bits]}                 = mem[reg[n]] ? pp += reg[k]
    # 10{n:[r bits]}{i:[m bits]}{<0/1>:[1 bit]}  = reg[n][i] = <0/1>
    # 11{n:[r bits]}{i:[m bits]}{k:[r bits]}     = reg[n][i] ? pp += reg[k]

    while True:
        regbit = (
            memread_1bit()
        )  # true - reg[n][i], false - mem[reg[n]] (aka [bit slot]: reg/mem)
        jmp = (
            memread_1bit()
        )  # true - pp += reg[k], false - write bit (aka [action]: condjmp/write)

        n = b2i(memread(r))
        regn = registers[n]

        match (regbit, jmp):
            case (False, False):
                regn_val = b2i(regn)
                b = memread_1bit()
                if b:  # check triggers
                    if regn_val == 0:
                        break  # halt
                    elif regn_val == 2:
                        # send stdout
                        stdout.fwd(mem[1])
                mem[regn_val] = b
                if debug:
                    print(f"mem[reg{n}:{regn_val}] = {int(b)}", end="")
            case (False, True):
                regn_val = b2i(regn)
                k = b2i(memread(r - 1) + [mem[pos]])
                regk = registers[k]
                regk_val = b2i(regk)
                add = regk_val if mem[regn_val] else 1
                pos = (pos + add) % sizeofmem
                if debug:
                    print(
                        f"mem[reg{n}:{regn_val}] ? pp:{pos} += reg{k}:{regk_val}",
                        end="",
                    )
            case (True, False):
                i = b2i(memread(m))
                regn[i] = memread_1bit()
                if debug:
                    print(f"reg{n}[{i}] = {int(regn[i])}", end="")
            case (True, True):
                i = b2i(memread(m))
                k = b2i(memread(r - 1) + [mem[pos]])
                regk = registers[k]
                regk_val = b2i(regk)
                add = regk_val if regn[i] else 1
                pos = (pos + add) % sizeofmem
                if debug:
                    print(f"reg{n}[{i}] ? pp:{pos} += reg{k}:{regk_val}", end="")
            case _:
                raise AssertionError()

        if debug:
            input()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A simple jaw vm")
    parser.add_argument(
        "--r",
        type=int,
        help="The register span (where there are 2^r registers) (int >= 1)",
        default=3,
    )
    parser.add_argument(
        "--m",
        type=int,
        help="The address space (where mem is of 2^2^m bits) (int >= 1)",
        default=4,
    )
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("program", type=str, help="The binary file to execute")
    args = parser.parse_args()
    exec_jaw(args.debug, args.r, args.m, args.program)
