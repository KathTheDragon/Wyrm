import re
from dataclasses import dataclass
from .nodes import *

## Constants
INDICATOR = r'([-=%:]|/[/!]|) ?'
SYNTAX_REGEXES = {
    'BLANK': re.compile(r'^ *$'),
    'INDENT': re.compile(fr'^( *){INDICATOR}'),
    'INLINE': re.compile(fr': *{INDICATOR}'),
    'KEYWORD': re.compile(r'[a-z]+'),
    'TEXT': re.compile(r'([^\\]|\\.)*?$')
}
NODE_DICT = {
    '': TextNode,
    '//': WyrmCommentNode,
    '/!': HTMLCommentNode,
    '%': HTMLTagNode,
    '=': ExpressionNode,
    'if': ConditionNode,
    'elif': ConditionNode,
    'else': ConditionNode,
    'for': ForNode,
    'empty': EmptyNode,
    'with': WithNode,
    'require': RequireNode,
    'include': IncludeNode,
    'block': BlockNode,
    'html': HTMLNode,
    'css': CSSNode,
    'js': JSNode,
    'md': MarkdownNode,
}

## Exceptions
class CompilerError(Exception):
    pass

## Classes
@dataclass
class Token:
    type: str
    value: str
    linenum: int
    column: int

## Functions
def tokenise(string):
    textindent = ''
    intext = False
    for linenum, line in enumerate(string.splitlines()):
        if SYNTAX_REGEXES['BLANK'].match(line) is not None:
            yield Token('NEWLINE', '', linenum, 0)
            continue
        match = SYNTAX_REGEXES['INDENT'].match(line)
        indent = match.group(1)
        indentcolumn = match.start(1)
        indicator = match.group(2)
        indicatorcolumn = match.start(2)
        column = match.end()
        if indicator == '':  # This line is text
            if intext:  # Already in text block
                if lastindent in indent:  # This line hasn't dedented
                    offset = len(indent) - len(lastindent)
                    indent = textindent
                    indicatorcolumn -= offset
                    column -= offset
                else:  # Dedented, treat like new text block
                    textindent = indent
            else:  # Entering text block
                intext = True
                textindent = indent
        elif intext:
            intext = False
        yield Token('INDENT', indent, linenum, indentcolumn)
        yield Token('INDICATOR', indicator, linenum, indicatorcolumn)
        yield from tokeniseLine(line, indicator, linenum, column)
        lastindent = indent
        lastindicator = indicator

def tokeniseLine(string, indicator, linenum=0, colstart=0):
    from .htmltag import tokenise as tokeniseHtml
    from .expression import tokenise as tokeniseExpression
    if indicator in ('', '//', '/!'):
        match = SYNTAX_REGEXES['TEXT'].match(string, colstart)
        yield Token('TEXT', match.group(), linenum, match.start())
        yield Token('NEWLINE', '', linenum, match.end())
        return
    elif indicator == '%':
        column = yield from tokeniseHtml(string, linenum, colstart)
    elif indicator == '=':
        column = yield from tokeniseExpression(string, linenum, colstart)
    elif indicator in ('-', ':'):
        match = SYNTAX_REGEXES['KEYWORD'].match(string, colstart)
        yield Token('KEYWORD', match.group(), linenum, match.start())
        column = yield from tokeniseExpression(string, linenum, match.end())
    else:
        raise CompilerError(f'invalid indicator: `{indicator}`')
    if column is None:
        column = len(string)
    match = SYNTAX_REGEXES['INLINE'].match(string, column)
    if match is not None:
        yield Token('INLINE', '', linenum, match.start())
        indicator = match.group(1)
        yield Token('INDICATOR', indicator, linenum, match.start(1))
        yield from tokeniseLine(string, indicator, linenum, match.end())
    else:
        yield Token('NEWLINE', '', linenum, column)

def compile(string):
    indents = [-1]
    nodes = [RootNode()]
    line = []
    for token in tokenise(string):
        if token.type != 'NEWLINE':
            line.append(token)
        else:  # End of line, compile
            if len(line) == 0:  # Blank line, special handling
                indent = indents[-1]
                if indent == -1:  # Leading blank line, can be ignored
                    line = []
                    continue
                _nodes = [TextNode()]
            else:
                indent = len(line[0].value)
                _nodes = compileLine(line[1:])
            _indents = [indent]*len(_nodes)
            while indent <= indents[-1]:
                if isinstance(_nodes[0], (EmptyNode, ConditionNode)) and isinstance(nodes[-1], (IfNode, ForNode)):
                    if indent == indents[-1]:
                        break
                    else:
                        raise CompilerError(f'unexpected {_nodes[0]!s}')
                indents.pop()
                node = nodes.pop()
                nodes[-1].append(node)
            if not isinstance(nodes[-1], NodeChildren):
                raise CompilerError(f'node {nodes[-1]!s} does not support children')
            nodes.extend(_nodes)
            indents.extend(_indents)
            line = []
    while True:  # Final compression and return
        node = nodes.pop()
        if nodes:
            nodes[-1].append(node)
        else:
            return node

def compileLine(tokens):
    indicator, line = tokens[0].value, tokens[1:]
    for i, token in enumerate(line):
        if token.type == 'INLINE':
            line, inlineNodes = line[:i], compileLine(line[i+1:])
            break
    else:
        inlineNodes = []
    if indicator in ('-', ':'):
        key, line = line[0].value, line[1:]
    else:
        key = indicator
    if key in ('else', 'empty') and line:
        raise TemplateError(f'`{key}` clause takes no arguments')
    node = NODE_DICT[key].make(line)
    if key == 'if':
        nodes = [IfNode(), node]
    elif key == 'for':
        nodes = [node, LoopNode()]
    else:
        nodes = [node]
    nodes.extend(inlineNodes)
    return nodes
