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
class VarList:
    vars: Tuple[str, ...]

    def __init__(self, vars):
        self.vars = tuple(vars)

    @staticmethod
    def make(tokens):
        vars = []
        i = 0
        for j in getCommas(tokens):
            if j == i:
                raise SyntaxError(tokens[i]))
            else:
                var = compile_tokens(tokens[i:j])
                if isinstance(var, Identifier):
                    var.append(var.name)
                else:
                    raise SyntaxError(tokens[i]))
            i = j+1
        return VarList(vars=vars)

    def __iter__(self):
        return iter(self.vars)

@dataclass
class VarDict:
    vars: Tuple[Tuple[str, Expression], ...]

    def __init__(self, vars):
        self.vars = tuple(vars)

    @staticmethod
    def make(tokens):
        vars = []
        i = 0
        for j in getCommas(tokens):
            if j == i:
                raise SyntaxError(tokens[i]))
            else:
                var = compile_tokens(tokens[i:j])
                if isinstance(var, BinaryOp) and var.op == '=':
                    if isinstance(var.left, Identifier):
                        vars.append((var.left.name, var.right))
                    else:
                        raise SyntaxError(tokens[i])
                else:
                    raise SyntaxError(tokens[i])
            i = j+1
        return VarDict(vars=vars)

    def evaluate(self, *contexts):
        return {var: expr.evaluate(*contexts) for var, expr in self.vars}

@dataclass
class AttrDict(VarDict):
    @staticmethod
    def make(tokens):
        attributes = []
        i = 0
        for j in getCommas(tokens):
            if j == i:
                raise SyntaxError(tokens[j]))
            else:
                attr = Expression.make(tokens[i:j])
                if isinstance(attr, BinaryOp) and attr.op == '=':
                    name, value = attr.left, attr.right
                else:
                    name, value = attr, Boolean(True)
                if isinstance(name, Identifier):
                    attributes.append((name.name, value))
                elif isinstance(name, String):
                    attributes.append((eval(name.string), value))
                else:
                    raise SyntaxError(tokens[i])
            i = j+1
        return AttrDict(vars=attributes)

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
            if j == i:
                if tokens[j].type == 'COMMA':
                    raise SyntaxError(tokens[j]))
            else:
                arg = compile_tokens(tokens[i:j])
                if isinstance(arg, BinaryOp) and arg.op == '=':
                    if isinstance(arg.left, Identifier):
                        kwargs.append((arg.left.name, arg.right))
                    else:
                        raise SyntaxError(tokens[i])
                else:
                    args.append(arg)
            i = j+1
        return ArgList(args=ListLiteral(args), kwargs=VarDict(kwargs))

    def evaluate(*contexts):
        return self.args.evaluate(*contexts), self.kwargs.evaluate(*contexts)

@dataclass
class Expression:
    @staticmethod
    def make(tokens):
        return compile_tokens(tokens)

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
class Boolean(Literal):
    truth: bool

    def __init__(self, truth):
        if truth == 'True':
            self.value == True
        elif truth == 'False':
            self.value == False

    def evaluate(*contexts):
        return self.truth

@dataclass
class NoneSingleton(Literal):
    def evaluate(*contexts):
        return None

@dataclass
class Sequence(Expression):
    items: tuple

    def __init__(self, items):
        self.items = tuple(items)

    @classmethod
    def make(cls, tokens):
        items = []
        i = 1
        for j in getCommas(tokens):
            if j == i:
                if tokens[j].type == 'COMMA':
                    raise SyntaxError(tokens[j])
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
                raise CompilerError(f'unexpected bracket', value, linenum, column)
            bracket = brackets.pop()
            if bracket+value not in ('()', '[]', '{}'):
                raise CompilerError(f'mismatched brackets', value, linenum, column)
        elif type == 'WHITESPACE':
            continue
        elif type == 'UNKNOWN':
            if not brackets:  # Probably a newline
                break
            raise CompilerError(f'unexpected character', value, linenum, column)
        yield Token(type, value, linenum, column)
    else:
        if brackets:
            raise CompilerError(f'unclosed bracket', brackets[-1], linenum, '_')
        yield Token('END', '', linenum, match.end()+colstart)
        return
    yield Token('END', '', linenum, column)

def compile_tokens(tokens):
    if not tokens:
        return None
    partials = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if expr is None:
            j = i + 1
            if token.type == 'OPERATOR':
                # Sanity check syntax
                if token.value in ('+', '-'):  # Unary and binary
                    pass
                elif token.value in ('~', 'not'):  # Unary only
                    if i != 0 and tokens[i-1].type != 'OPERATOR':
                        raise SyntaxError(token)
                else:  # Binary only
                    if i == 0 or tokens[i-1].type == 'OPERATOR':
                        raise SyntaxError(token)
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
                    else:
                        raise SyntaxError(token)
            elif token.type == 'KEYWORD':
                if token.value in ('True', 'False'):
                    partials.append(Boolean(token.value))
                elif token.value == 'None':
                    partials.append(NoneType())
            elif token.type == 'IDENTIFIER':
                partials.append(Identifier(token.value))
            elif token.type == 'STRING':
                partials.append(String(token.value))
            elif token.type == 'NUMBER':
                partials.append(Number(token.value))
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
    partials = compileBinaryOps(partials, ('=', ':'))  # Pairing 'ops'
    # if-else (maybe)
    # lambda (maybe)
    if len(partials) != 1:
        raise ExpressionError('invalid expression')
    return partials[0]

## Helper Functions
def matchBrackets(tokens):
    if tokens[0].type != 'LBRACKET':
        raise TokenError('expected bracket', token)
    depth = 0
    for i, token in enumerate(tokens, 1):
        if token.type == 'LBRACKET':
            depth += 1
        elif token.type == 'RBRACKET':
            depth -= 1
            if count == 0:
                return i
    raise TokenError('unmatched bracket', token)

def getCommas(tokens):
    depth = 0
    for i, token in enumerate(tokens):
        if token.type == 'COMMA' and depth == 1:
            yield i
        elif token.type == 'LBRACKET':
            depth += 1
        elif token.type == 'RBRACKET':
            depth -= 1
    if tokens[-1].type == 'RBRACKET':
        yield i
    else:
        yield i + 1

def compileBinaryOps(partials, operators):
    partials = partials.copy()
    i = 0
    while i < len(partials):
        if partials[i] in operators:
            partials[i-1:i+2] = [BinaryOp(partials[i], partials[i-1], partials[i+1])]
        else:
            i += 1
    return partials
