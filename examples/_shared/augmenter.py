from dataclasses import dataclass
import re
import sys
from typing import Any, Callable, List, Tuple


class Return:
    content: str

    def __init__(self, content: str):
        self.content = content

    @property
    def hex(self) -> str:
        raise NotImplementedError()

    @property
    def bin(self) -> str:
        raise NotImplementedError()

    @property
    def get(self) -> str:
        raise NotImplementedError()


@dataclass
class HexReturn(Return):
    def __init__(self, content: str):
        self.content = content

    @property
    def bin(self):
        return bin(int(self.content, 16))[2:]

    @property
    def hex(self):
        return self.content

    @property
    def get(self):
        return "0x" + self.content


@dataclass
class BinReturn(Return):
    def __init__(self, content: str):
        self.content = content

    @property
    def bin(self):
        return self.content

    @property
    def hex(self):
        return hex(int(self.content, 2))[2:]

    @property
    def get(self):
        return "0xb" + self.content


@dataclass
class Range:
    min: int
    max: int | None

    @staticmethod
    def only(value: int):
        return Range(min=value, max=value)

    @property
    def ensure_max(self):
        assert self.max is not None
        return self.max


@dataclass
class Command:
    regex: re.Pattern[Any]
    func: Callable[..., Return]
    eval_args: Callable[[Tuple[str], List[int]], str]
    labels: Callable[[Tuple[str]], List[str]]
    _range: Callable[[], Range]

    @property
    def range(self):
        return self._range()


commands: List[Command] = []
offset: int
r: int
m: int

registers_count: int
sizeofreg: int

parambr = re.compile(r"\{:(\S+?):\}")


@dataclass
class ParamResolver:
    resolve: Callable[[str, List[int]], Any]  # (matched arg, labels) => res | None
    label: Callable[[str], str | None]  # (matched arg) => label | None


@dataclass
class ParamT:
    selector: re.Pattern[Any]
    resolve: Callable[
        [str, str, List[int]], Any
    ]  # (matched_selector, matched arg, labels) => res | None
    label: Callable[[str, str], str | None]  # (matched_selector, matched arg)

    def gen_resolver(self, s: str):
        matched_selector = self.selector.fullmatch(s)
        if matched_selector is None:
            return None
        return ParamResolver(
            resolve=lambda arg, lbs: self.resolve(s, arg, lbs),
            label=lambda arg: self.label(s, arg),
        )


param_resolvers: List[ParamT] = []

param_resolvers.append(
    ParamT(
        selector=re.compile(r"N"),
        resolve=lambda sm, arg, lbls: int(arg, base=0),
        label=lambda sm, arg: None,
    )
)

param_resolvers.append(
    ParamT(
        selector=re.compile(r"S"),
        resolve=lambda sm, arg, lbls: arg,
        label=lambda sm, arg: None,
    )
)

param_resolvers.append(
    ParamT(
        selector=re.compile(r"X"),
        resolve=lambda sm, arg, lbls: lbls.pop(0) if arg.startswith(".") else None,
        label=lambda sm, arg: arg[1:] if arg.startswith(".") else None,
    )
)

param_resolvers.append(
    ParamT(
        selector=re.compile(r"\`\S*\`"),
        resolve=lambda sm, arg, lbls: arg if arg == sm[1:-1] else None,
        label=lambda sm, arg: None,
    )
)


def get_param_resolver(s: str):
    for rlvr in param_resolvers:
        r = rlvr.gen_resolver(s)
        if r is not None:
            return r
    raise AssertionError(f"Failed to find parameter resolver for {s}")


def get_mixed_params_resolver(s: str):
    mix = s.split("|")
    assert len(mix) != 0, f"Empty mixed param: {mix}"
    return [get_param_resolver(e) for e in mix]


def add_to_commands(pattern: str, range: Callable[[], Range]) -> Callable[..., Command]:
    def decorate(func: Callable[..., Return]) -> Command:
        escaped_pattern = re.escape(pattern).replace(r"\{:", "{:").replace(r":\}", ":}")
        regex_pattern = parambr.sub(r"(\\S*)", escaped_pattern)
        regex = re.compile(rf"^{regex_pattern}$")
        params = [get_mixed_params_resolver(p) for p in parambr.findall(pattern)]

        def eval_args(args: Tuple[str], labels: List[int]) -> str:
            cargs: List[Any] = []
            for param, arg in zip(params, args):
                carg: Any
                for resolvep in param:
                    carg = resolvep.resolve(arg, labels)
                    if carg is not None:
                        break
                else:
                    raise ValueError(f"invalid value : {arg}")
                cargs.append(carg)
            return func(*cargs).get

        def labels_wrapper(args: Tuple[str]):
            labels: List[str] = []
            for param, arg in zip(params, args):
                for resolvep in param:
                    lbl = resolvep.label(arg)
                    if lbl is not None:
                        labels.append(lbl)
                        break  # one label per parameter
            return labels

        cmd = Command(
            regex=regex,
            func=func,
            eval_args=eval_args,
            labels=labels_wrapper,
            _range=range,
        )
        commands.append(cmd)
        return cmd

    return decorate


def mb(n: int, size: int):
    if n >= 2**size:
        raise ValueError(f"Value of {n} cannot fit into {size} bits.")
    return f"{n:0{size}b}"


# # Basic instructions
@add_to_commands(
    "mem[reg{:N:}] = {:N:}",
    range=lambda: Range.only(3 + r),
)
def set_mem_bit(n: int, b: int):
    # 00{n:[r bits]}{<0/1>:[1 bit]}
    return BinReturn(f"00{mb(n, r)}{mb(b, 1)}")


@add_to_commands(
    "mem[reg{:N:}] ? pp += reg{:N:}",
    range=lambda: Range.only(2 + r * 2),
)
def cnd_jmp_mem(n: int, k: int):
    # 01{n:[r bits]}{k:[r bits]}
    return BinReturn(f"01{mb(n, r)}{mb(k, r)}")


@add_to_commands(
    "reg[{:N:}][{:N:}] = {:N:}",
    range=lambda: Range.only(3 + r + m),
)
def set_reg_bit(n: int, i: int, b: int):
    # 10{n:[r bits]}{i:[m bits]}{<0/1>:[1 bit]}
    return BinReturn(f"10{mb(n, r)}{mb(i, m)}{mb(b, 1)}")


@add_to_commands(
    "reg{:N:}[{:N:}] ? pp += reg{:N:}",
    range=lambda: Range.only(2 + 2 * r + m),
)
def cnd_jmp_reg(n: int, i: int, k: int):
    # 11{n:[r bits]}{i:[m bits]}{k:[r bits]}
    return BinReturn(f"11{mb(n, r)}{mb(i, m)}{mb(k, r)}")


# TODO: in case of `reg0: 0x0 = const 0x0` it might actually respond with strict evaluation of the range
# # Complex instructions
@add_to_commands(
    "reg{:N:}: {:`any`|X|N:} = const {:X|N:}",
    range=lambda: Range(0, sizeofreg * set_reg_bit.range.ensure_max),
)
def set_full_reg_with_const(n: int, init: str | int, const: int):
    if init == "any":
        return BinReturn(set_full_reg_from_any(n, const))

    assert isinstance(init, int)
    return BinReturn(set_full_reg_from_known(n, init, const))


def set_full_reg_from_known(n: int, init: int, const: int):
    res = ""
    for i, wasbit, needbit in zip(
        range(sizeofreg), mb(init, sizeofreg), mb(const, sizeofreg)
    ):
        if wasbit != needbit:
            res += set_reg_bit.func(n, i, int(needbit)).bin
    return res


def set_full_reg_from_any(n: int, const: int):
    return "".join(
        set_reg_bit.func(n, i, int(bit)).bin
        for i, bit in enumerate(mb(const, sizeofreg))
    )


@add_to_commands(
    "reg{:N:}: {:`any`|X|N:} = const {:X|N:} - {:X|N:}",
    range=lambda: Range(0, sizeofreg * set_reg_bit.range.ensure_max),
)
def set_full_reg_with_const_diff(n: int, init: str | int, a: int, b: int):
    return set_full_reg_with_const.func(n, init, a - b)


# TODO: regN == X ? pp = X
# TODO: regN[N] = mem[regN]
# TODO: regN++


@add_to_commands(
    '#store_unicode "{:S:}"',
    range=lambda: Range(0, None),
)
def store_unicode(s: str):
    s = s.encode().decode("unicode-escape")
    res = ""
    for ch in s:
        res += f"{ord(ch):04x}"
    return HexReturn(res)


@add_to_commands(
    '#dumb_stdout "{:S:}"',
    range=lambda: Range(0, None),
)
def dumb_stdout(s: str):
    # assumes reg1 is set to 0x1, reg2 is set to 0x2
    s = s.encode().decode("unicode-escape")
    res = ""
    for ch in s:
        for bit in f"{ord(ch):016b}":
            res += set_mem_bit.func(1, int(bit)).bin  # mem[reg1] = bit // set data
            res += set_mem_bit.func(2, 1).bin  # mem[reg2] = 1 // trigger collect
    return BinReturn(res)


if __name__ == "__main__":
    _, _offset, _r, _m, _f, msg, *labels = sys.argv
    offset = int(_offset, base=16)  # use for computation of labels
    r = int(_r)
    m = int(_m)

    registers_count = 2**r
    sizeofreg = 2**m

    labels = [int(label, base=0) for label in labels]

    for cmd in commands:
        match = cmd.regex.search(msg)
        if match is None:
            continue
        args = match.groups()
        match _f:
            case "?":
                rng = cmd.range
                labels_names = cmd.labels(args)  # type: ignore
                print(
                    f"{rng.min:x}-{'inf' if rng.max is None else hex(rng.max)[2:]} {' '.join(labels_names)}"
                )
            case ">":
                print(cmd.eval_args(args, labels))  # type: ignore
                assert len(labels) == 0
            case _:
                raise ValueError(f"{_f} is not ? or >")
        break
    else:
        raise ValueError(msg)
