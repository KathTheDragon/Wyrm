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
ESCAPES = {
    't': '\t',
    'n': '\n',
    '{': '{"{"}',
}
TOKENS = {
    'OPERATOR': r'[-+@&|^~:]|[<>!=]?=|[*/<>]{1,2}|('+'|'.join(KEYWORD_OPERATORS)+r')(?!\w)',
    'DOT': r'\.',
    'COMMA': r',',
    'LBRACKET': r'[([{]',
    'RBRACKET': r'[}\])]',
    'KEYWORD': '('+'|'.join(KEYWORDS)+r')(?!\w)',
    'IDENTIFIER': r'[a-zA-Z_]\w*',
    'STRING': fr'\'{STRING}\'|\"{STRING}\"',
    'NUMBER': r'\d+\.?\d*',
    'WHITESPACE': r' +',
    'UNKNOWN': r'.'
}
TOKEN_REGEX = re.compile('|'.join(f'(?P<{type}>{regex})' for type, regex in TOKENS.items()))

## Exceptions
class CompilerError(Exception):
    def __init__(self, error, value, linenum, column):
        super().__init__(f'{error}: `{value}` @ {linenum}:{column}')

class TokenError(CompilerError):
    def __init__(self, error, token):
        super().__init__(error, token.value, token.linenum, token.column)

class UnexpectedTokenError(TokenError):
    def __init__(self, token):
        super().__init__('unexpected token', token)

class SyntaxError(TokenError):
    def __init__(self, token):
        super().__init__('invalid syntax', token)

class ExpressionError(Exception):
    pass

## Classes
@dataclass
class FormalList:
    vars: tuple

    @classmethod
    def make(cls, tokens=()):
        vars = []
        for item, sep in partitionList(tokens):
            if not item:
                raise SyntaxError(sep)
            var = self.makeVar(compileTokens(item))
            if var is None:
                raise SyntaxError(item[0])
            else:
                vars.append(var)
        return cls(vars=tuple(vars))

    @staticmethod
    def makeVar(item):
        return item

@dataclass
class VarList(FormalList):
    vars: Tuple[str, ...]

    def __len__(self):
        return len(self.vars)

    def __getitem__(self, item):
        return self.vars[item]

    def __iter__(self):
        yield from self.vars

    @staticmethod
    def makeVar(item):
        if isinstance(item, Identifier):
            return item.name
        return None

@dataclass
class VarDict(FormalList):
    vars: Tuple[Tuple[str, 'Expression'], ...]

    @staticmethod
    def makeVar(item):
        if isinstance(item, BinaryOp) and item.op == '=':
            if isinstance(item.left, Identifier):
                return (item.left.name, item.right)
        return None

    def evaluate(self, *contexts):
        return {var: expr.evaluate(*contexts) for var, expr in self.vars}

@dataclass
class AttrDict(VarDict):
    @staticmethod
    def makeVar(item):
        if isinstance(item, BinaryOp) and item.op == '=':
            name, value = item.left, item.right
        else:
            name, value = item, Boolean(True)
        if isinstance(name, Identifier):
            return (name.name, value)
        elif isinstance(name, String):
            return (name.string, value)
        return None

@dataclass
class ArgList:
    args: 'ListLiteral'
    kwargs: VarDict

    @staticmethod
    def make(tokens=()):
        args = []
        kwargs = []
        for item, sep in partitionList(tokens):
            if not item:
                if sep is not None:
                    raise SyntaxError(sep)
            arg = compileTokens(item)
            if isinstance(arg, BinaryOp) and arg.op == '=':
                if isinstance(arg.left, Identifier):
                    kwargs.append((arg.left.name, arg.right))
                else:
                    raise SyntaxError(tokens[i])
            else:
                args.append(arg)
        return ArgList(args=ListLiteral(tuple(args)), kwargs=VarDict(tuple(kwargs)))

    def evaluate(self, *contexts):
        return self.args.evaluate(*contexts), self.kwargs.evaluate(*contexts)

@dataclass
class Expression:
    @classmethod
    def make(cls, tokens):
        expr = compileTokens(tokens)
        if cls == Expression or isinstance(expr, cls):
            return expr
        else:
            raise ExpressionError(f'expression is not of type {cls.__name__}')

    def evaluate(self, *contexts):
        return

@dataclass
class Literal(Expression):
    pass

@dataclass
class Identifier(Literal):
    name: str

    def evaluate(self, *contexts):
        name = self.name
        for context in contexts:
            if name in context:
                return context[name]
        return ''

re_escape = re.compile(r'\\(.)')  # Used to delete the slash in escape sequences
re_format = re.compile(r'{(.+?)}')  # Used to target formatting brackets

@dataclass
class String(Literal):
    string: str

    def evaluate(self, *contexts):
        string = re_escape.sub(lambda m: ESCAPES.get(m[1], m[1]), self.string)
        return re_format.sub(lambda m: str(compile(m[1]).evaluate(*contexts)), string)

@dataclass
class Number(Literal):
    number: float

    def evaluate(self, *contexts):
        return self.number

@dataclass
class Boolean(Literal):
    truth: bool

    def evaluate(self, *contexts):
        return self.truth

@dataclass
class NoneSingleton(Literal):
    def evaluate(*contexts):
        return None

@dataclass
class Sequence(Expression):
    items: tuple

    @classmethod
    def make(cls, tokens):
        items = []
        for item, sep in partitionList(tokens):
            if not item:
                if sep is not None:
                    raise SyntaxError(sep)
                if cls == TupleLiteral:
                    items.append(None)
            else:
                items.append(compileTokens(item))
        return cls(tuple(items))

@dataclass(init=False)
class TupleLiteral(Sequence):
    items: Tuple[Expression, ...]

    def evaluate(self, *contexts):
        if len(self.items) == 1:
            return self.items[0].evaluate(*contexts)
        return tuple(item.evaluate(*contexts) for item in self.items if item is not None)

@dataclass(init=False)
class ListLiteral(Sequence):
    items: Tuple[Expression, ...]

    def evaluate(self, *contexts):
        return [item.evaluate(*contexts) for item in self.items]

@dataclass(init=False)
class DictLiteral(Sequence):
    items: Tuple[Tuple[Expression, Expression], ...]

    def evaluate(self, *contexts):
        return {key.evaluate(*contexts): value.evaluate(*contexts) for key, value in self.items}

@dataclass
class Compound(Expression):
    pass

@dataclass
class Dotted(Compound):
    expr: Expression
    attr: str

    def evaluate(self, *contexts):
        expr = self.expr.evaluate(*contexts)
        if not hasattr(expr, self.attr):
            raise ExpressionError(f'{expr!r} has no attribute {attr!r}')
        return getattr(expr, self.attr)

@dataclass
class Subscripted(Compound):
    expr: Expression
    subscript: Expression

    def evaluate(self, *contexts):
        expr = self.expr.evaluate(*contexts)
        if not hasattr(expr, '__getitem__'):
            raise ExpressionError(f'{expr!r} is not subscriptable')
            subscript = self.subscript.evaluate(*contexts)
        return expr[subscript]

@dataclass
class Call(Compound):
    name: Union[Identifier, Compound]
    args: ArgList

    def evaluate(self, *contexts):
        name = self.name.evaluate(*contexts)
        if not hasattr(name, '__call__'):
            raise ExpressionError(f'{name!r} is not callable')
        args, kwargs = self.args.evaluate(*contexts)
        return name(*args, **kwargs)

@dataclass
class Operator(Expression):
    op: str

@dataclass
class UnaryOp(Operator):
    arg: Expression

    def evaluate(self, *contexts):
        op = self.op
        arg = self.arg.evaluate(*contexts)
        return eval(f'{op} {arg!r}')

@dataclass
class BinaryOp(Operator):
    left: Expression
    right: Expression

    def evaluate(self, *contexts):
        op = self.op
        left = self.left.evaluate(*contexts)
        right = self.right.evaluate(*contexts)
        if op == '=':
            raise ExpressionError(f'invalid operation: {op}')
        return eval(f'{left!r} {op} {right!r}')

## Functions
def tokenise(string, linenum=None, colstart=0):  # Perhaps I might enforce expression structure here
    from .compiler import Token, CompilerError
    if colstart >= len(string):
        return
    if linenum is None:
        nested = False
        linenum = 0
    else:
        nested = True
    brackets = []
    for match in TOKEN_REGEX.finditer(string, colstart):
        type = match.lastgroup
        value = match.group()
        column = match.start()
        if type == 'OPERATOR' and value == ':':
            if not brackets:  # Inline operator
                if nested:
                    return column
                raise CompilerError(f'unexpected character', value, linenum, column)
        elif type == 'LBRACKET':
            brackets.append(value)
        elif type == 'RBRACKET':
            if not brackets:
                raise CompilerError(f'unexpected bracket', value, linenum, column)
            bracket = brackets.pop()
            if bracket+value not in ('()', '[]', '{}'):
                raise CompilerError(f'mismatched brackets', value, linenum, column)
        elif type == 'WHITESPACE':
            continue
        elif type == 'UNKNOWN':
            if nested and not brackets:  # Probably a newline
                return column
            raise CompilerError(f'unexpected character', value, linenum, column)
        yield Token(type, value, linenum, column)
    if brackets:
        raise CompilerError(f'unclosed bracket', brackets[-1], linenum, '_')

def compile(string):
    return compileTokens(tokenise(string))

def compileTokens(tokens):
    tokens = list(tokens)
    if not tokens:
        return None
    partials = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        j = i + 1
        if token.type == 'OPERATOR':
            # Sanity check syntax
            if token.value in ('+', '-'):  # Unary and binary
                pass
            elif token.value in ('~', 'not'):  # Unary only
                if i != 0 and tokens[i-1].type != 'OPERATOR':
                    raise SyntaxError(token)#
            else:  # Binary only
                if i == 0 or tokens[i-1].type == 'OPERATOR':
                    raise SyntaxError(token)#
            partials.append(token.value)
        elif token.type == 'DOT':
            if tokens[i-1].type == 'OPERATOR' or tokens[i+1].type != 'IDENTIFIER':
                raise SyntaxError(token)
            partials.append(Dotted(partials.pop(), token.value))
        elif token.type == 'LBRACKET':
            j = i + matchBrackets(tokens[i:])
            if i == 0 or tokens[i-1].type == 'OPERATOR':  # Literal
                if token.value == '(':
                    cls = TupleLiteral
                elif token.value == '[':
                    cls = ListLiteral
                elif token.value == '{':
                    cls = DictLiteral
                else:  # Unexpected token
                    raise UnexpectedTokenError(token)
                partials.append(cls.make(tokens[i:j]))
            else:
                if token.value == '(':  # Argument list
                    partials.append(Call(partials.pop(), ArgList.make(tokens[i:j])))
                elif token.value == '[':  # Subscript
                    partials.append(Subscripted(partials.pop(), TupleLiteral.make(tokens[i:j])))
                else:#
                    raise SyntaxError(token)#
        elif token.type == 'KEYWORD':
            if token.value in ('True', 'False'):
                partials.append(Boolean(eval(token.value)))
            elif token.value == 'None':
                partials.append(NoneType())
        elif token.type == 'IDENTIFIER':
            partials.append(Identifier(token.value))
        elif token.type == 'STRING':
            partials.append(String(eval(token.value)))
        elif token.type == 'NUMBER':
            partials.append(Number(eval(token.value)))
        else:  # Unexpected token
            raise UnexpectedTokenError(token)
        i = j
    # Unary ops
    for i in reversed(range(len(partials))):
        if partials[i] in UNARY_OPERATORS and (i == 0 or isinstance(partials[i-1], str)):
            partials[i:i+2] = [UnaryOp(partials[i], partials[i+1])]
    # Power op - is right-associative so must be done this way
    for i in reversed(range(len(partials))):
        if partials[i] == '**':
            partials[i-1:i+2] = [BinaryOp('**', partials[i-1], partials[i+1])]
    partials = compileBinaryOps(partials, ('*', '@', '/', '//', '%'))  # Multiplicative ops
    partials = compileBinaryOps(partials, ('+', '-'))  # Additive ops
    partials = compileBinaryOps(partials, ('<<', '>>'))  # Bitshift ops
    partials = compileBinaryOps(partials, ('&',))  # Bitwise and
    partials = compileBinaryOps(partials, ('^',))  # Bitwise xor
    partials = compileBinaryOps(partials, ('|',))  # Bitwise or
    partials = compileBinaryOps(partials, ('in', 'not in', 'is', 'is not', '<', '<=', '>', '>=', '!=', '=='))  # Comparison
    partials = compileBinaryOps(partials, ('and',))  # and
    partials = compileBinaryOps(partials, ('or',))  # or
    # 'Pairing' ops - `=` does not feature normally and `:` requires special handling
    for i in reversed(range(len(partials))):
        if partials[i] == '=':
            partials[i-1:i+2] = [BinaryOp('=', partials[i-1], partials[i+1])]
        elif partials[i] == ':':
            partials[i-1:i+2] = [(partials[i-1], partials[i+1])]
    # if-else (maybe)
    # lambda (maybe)
    if len(partials) != 1:
        raise ExpressionError('invalid expression')
    return partials[0]

## Helper Functions
def matchBrackets(tokens):
    if tokens[0].type != 'LBRACKET':
        raise TokenError('expected bracket', tokens[0])
    depth = 0
    for i, token in enumerate(tokens, 1):
        if token.type == 'LBRACKET':
            depth += 1
        elif token.type == 'RBRACKET':
            depth -= 1
            if depth == 0:
                return i
    raise TokenError('unmatched bracket', tokens[0])

def partition(sequence, *, sep=None, sep_func=None, nest_func=None, yield_sep=False):
    if not sequence:
        return
    if sep is None == sep_func is None:
        raise ValueError('exactly one of separator and separator_func must be given')
    if sep is not None:
        sep_func = lambda item: item == sep
    if nest_func is None:
        nest_func = lambda item: 0
    depth = 0
    edges = (nest_func(sequence[0]), nest_func(sequence[-1]))
    if edges == (1, -1):
        i = 1
        k = -1
    elif edges[0] == 1 or edges[1] == -1:
        raise ValueError('sequence is improperly nested')
    else:
        i = 0
        k = None
    for j, item in enumerate(sequence):
        if sep_func(item) and depth == _depth:
            if yield_sep:
                yield (sequence[i:j], item)
            else:
                yield sequence[i:j]
            i = j+1
        depth += nest_func(item)
    if yield_sep:
        yield sequence[i:k], None
    else:
        yield sequence[i:k]

def partitionList(sequence):
    sep_func = lambda token: token.type == 'COMMA'
    nest_func = lambda token: 1 if token.type == 'LBRACKET' else -1 if token.type == 'RBRACKET' else 0
    yield from partition(sequence, sep_func=sep_func, nest_func=nest_func, yield_sep=True)

def compileBinaryOps(partials, operators):
    partials = partials.copy()
    i = 0
    while i < len(partials):
        if partials[i] in operators:
            partials[i-1:i+2] = [BinaryOp(partials[i], partials[i-1], partials[i+1])]
        else:
            i += 1
    return partials
