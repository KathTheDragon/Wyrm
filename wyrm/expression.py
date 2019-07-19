from dataclasses import dataclass
from typing import Tuple, Dict, Union
import re

## Constants
KEYWORDS = [
    'False',
    'None',
    'True',
    'elif',
    'else',
    'for',
    'if',
    # 'lambda',
    'only',
    'with',
]
KEYWORD_OPERATORS = [
    'and',
    'in',
    'is not',
    'is',
    'not in',
    'not',
    'or',
]
UNARY_OPERATORS = [
    '+',
    '-',
    '~',
    'not'
]
STRING = r'([^\\\n]|\\.)*?'
TOKENS = {
    'OPERATOR': r'[-+@&|^~:]|[<>!=]?=|[*/<>]{1,2}|'+'|'.join(KEYWORD_OPERATORS),
    'DOT': r'\.',
    'COMMA': r',',
    'LBRACKET': r'[([{]',
    'RBRACKET': r'[}\])]',
    'KEYWORD': '|'.join(KEYWORDS),
    'IDENTIFIER': r'[a-zA-Z_]\w*',
    'STRING': fr'\'{STRING}\'|\"{STRING}\"',
    'NUMBER': r'\d+\.?\d*',
    'WHITESPACE': r' +',
    'UNKNOWN': r'.'
}
TOKEN_REGEX = re.compile('|'.join(f'(?P<{type}>{regex})' for type, regex in TOKENS.items()))

## Exceptions
class CompilerError(Exception):
    pass

class ExpressionError(Exception):
    pass

## Classes
@dataclass
class VarList:
    vars: Tuple[str, ...]

    @staticmethod
    def make(tokens):
        pass

    def __iter__(self):
        return iter(self.vars)

@dataclass
class VarDict:
    vars: Tuple[Tuple[str, Expression], ...]

    @staticmethod
    def make(tokens):
        pass

    def evaluate(self, *contexts):
        return {var: expr.evaluate(*contexts) for var, expr in self.vars}

@dataclass
class ArgList:
    args: ListLiteral
    kwargs: VarDict

    @staticmethod
    def make(tokens):
        args = []
        kwargs = []
        i = 1
        for j in getCommas(tokens):
            if j == i + 1:
                if tokens[j].type == 'COMMA':
                    raise CompilerError(f'invalid syntax: `{token.value}` @ {token.linenum}:{token.column}')
            else:
                arg = compile_tokens(tokens[i:j])
                if isinstance(arg, BinaryOp):
                    if isinstance(arg.left, Identifier):
                        kwargs.append((arg.left.name, arg.right))
                    else:
                        raise CompilerError(f'invalid syntax: `{tokens[i].value}` @ {tokens[i].linenum}:{tokens[i].column}')
                else:
                    args.append(arg)
            i = j + 1
        return ArgList(ListLiteral(tuple(args)), VarDict(tuple(kwargs)))

    def evaluate(*contexts):
        return self.args.evaluate(*contexts), self.kwargs.evaluate(*contexts)

@dataclass
class Expression:
    @staticmethod
    def make(tokens):
        return Expression()

    def evaluate(self, *contexts):
        return

@dataclass
class Literal(Expression):
    @classmethod
    def make(cls, tokens):
        name = cls.__name__.lower()
        if len(tokens) != 1:
            raise ExpressionError(f'{name}s can only take a single token')
        token = tokens[0]
        if token.type == name.upper():
            return cls(token.value)
        else:
            raise ExpressionError(f'{name}s take a token of type {name.upper()!r}, not {token.type!r}')

@dataclass
class Identifier(Literal):
    name: str

    def evaluate(self, *contexts):
        name = self.name
        for context in contexts:
            if name in context:
                return context[name]

re_slashes = re.compile(r'(\\+)\1')
re_format = re.compile(r'(\\?){(.*?)}')

@dataclass
class String(Literal):
    string: str

    def evaluate(self, *contexts):
        strings = re_slashes.split(self.string)
        for i, string in enumerate(strings):
            strings[i] = re_format.sub(lambda m: string_format(m, *contexts), string)
        return ''.join(strings)

@dataclass
class Number(Literal):
    number: float

    def __init__(self, number):
        if '.' in number:
            self.number = float(number)
        else:
            self.number = int(number)

    def evaluate(self, *contexts):
        return self.number

@dataclass
class Sequence(Expression):
    @classmethod
    def make(cls, tokens):
        items = []
        i = 1
        for j in getCommas(tokens):
            if j == i + 1:
                if tokens[j].type == 'COMMA':
                    raise CompilerError(f'invalid syntax: `{token.value}` @ {token.linenum}:{token.column}')
                if cls == TupleLiteral:
                    items.append(None)
            else:
                items.append(compile_tokens(tokens[i:j]))
            i = j + 1
        return cls(tuple(items))

@dataclass
class TupleLiteral(Sequence):
    items: Tuple[Expression, ...]

    def evaluate(self, *contexts):
        if len(self.items) == 1:
            return self.items[0].evaluate(*contexts)
        return tuple(item.evaluate(*contexts) for item in self.items if item is not None)

@dataclass
class ListLiteral(Sequence):
    items: Tuple[Expression, ...]

    def evaluate(self, *contexts):
        return [item.evaluate(*contexts) for item in self.items]

@dataclass
class DictLiteral(Sequence):
    items: Tuple[Tuple[Expression, Expression], ...]

    def evaluate(self, *contexts):
        return {key.evaluate(*contexts): value.evaluate(*contexts) for key, value in self.items}

@dataclass
class Operator(Expression):
    op: str

@dataclass
class UnaryOp(Operator):
    arg: Expression

    def evaluate(*contexts):
        op = self.op
        arg = self.arg.evaluate(*contexts)
        return eval(f'{op} {arg!r}')

@dataclass
class BinaryOp(Operator):
    left: Expression
    right: Expression

    def evaluate(*contexts):
        op = self.op
        left = self.left.evaluate(*contexts)
        right = self.right.evaluate(*contexts)
        return eval(f'{left!r} {op} {right!r}')

## Functions
def tokenise(string, linenum=0, colstart=0):  # Perhaps I might enforce expression structure here
    from .compiler import Token, CompilerError
    brackets = []
    for match in TOKEN_REGEX.finditer(string):
        type = match.lastgroup
        value = match.group()
        column = match.start() + colstart
        if type == 'OPERATOR' and value == ':':
            if not brackets:  # Inline operator
                break
        elif type == 'LBRACKET':
            brackets.append(value)
        elif type == 'RBRACKET':
            if not brackets:
                raise CompilerError(f'unexpected bracket: `{value}` @ {linenum}:{column}')
            bracket = brackets.pop()
            if bracket+value not in ('()', '[]', '{}'):
                raise CompilerError(f'mismatched brackets: `{value}` @ {linenum}:{column}')
        elif type == 'WHITESPACE':
            continue
        elif type == 'UNKNOWN':
            if not brackets:  # Probably a newline
                break
            raise CompilerError(f'unexpected character: `{value}` @ {linenum}:{column}')
        yield Token(type, value, linenum, column)
    else:
        if brackets:
            raise CompilerError(f'unclosed bracket `{brackets[-1]}` @ {linenum}:_')
        yield Token('END', '', linenum, match.end()+colstart)
        return
    yield Token('END', '', linenum, column)
