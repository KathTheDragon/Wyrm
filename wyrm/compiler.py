import re
from dataclasses import dataclass
from .nodes import *

## Constants
INDICATOR = r'([-=/%:]|/!|) ?'
SYNTAX_REGEXES = {
    'BLANK': re.compile(r'^ *$', flags=re.M),
    'INDENT': re.compile(fr'^( *){INDICATOR}', flags=re.M),
    'INLINE': re.compile(fr': *{INDICATOR}'),
    'KEYWORD': re.compile(r'[a-z]+'),
    'TEXT': re.compile(r'([^\\]|\\.)*?$', flags=re.M)
}
NODE_DICT = {
    '': TextNode,
    '/': CommentNode,
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
    line: int
    column: int

## Functions
def tokenise(string):
    for linenum, line in enumerate(string.splitlines()):
        if SYNTAX_REGEXES['BLANK'].match(line) is not None:
            yield Token('NEWLINE', '', linenum, 0)
            continue
        match = SYNTAX_REGEXES['INDENT'].match(line)
        yield Token('INDENT', match.group(1), linenum, match.start(1))
        indicator = match.group(2)
        yield Token('INDICATOR', indicator, linenum, match.start(2))
        column = match.end()
        yield from tokenise_line(line[column:], indicator, linenum, column)

def tokenise_line(string, indicator, linenum=0, colstart=0):
    from .htmltag import tokenise as tokenise_html
    from .expression import tokenise as tokenise_expression
    if indicator in ('', '/', '/!'):
        match = SYNTAX_REGEXES['TEXT'].match(string)
        yield Token('TEXT', match.group(), linenum, match.start()+colstart)
        yield Token('NEWLINE', '', linenum, match.end()+colstart)
        return
    elif indicator == '%':
        for token in tokenise_html(string, linenum, colstart):
            if token.type == 'END':
                break
            yield token
    elif indicator in ('-', '=', ':'):
        if indicator == '=':
            column = 0
        else:
            match = SYNTAX_REGEXES['KEYWORD'].match(string)
            yield Token('KEYWORD', match.group(), linenum, match.start()+colstart)
            column = match.end()
        for token in tokenise_expression(string[column:], linenum, column+colstart):
            if token.type == 'END':
                break
            yield token
    else:
        raise CompilerError(f'invalid indicator: `{indicator}`')
    match = SYNTAX_REGEXES['INLINE'].match(string, token.column-colstart)
    if match is not None:
        yield Token('INLINE', '', linenum, match.start()+colstart)
        indicator = match.group(1)
        column = match.end()
        yield Token('INDICATOR', indicator, linenum, match.start(1)+colstart)
        yield from tokenise_line(string[column:], indicator, linenum, column+colstart)
    else:
        yield Token('NEWLINE', '', linenum, token.column)

def compile_tokens(tokens):
    indents = [-1]
    nodes = [RootNode()]
    line = []
    for token in tokens:
        if token.type != 'NEWLINE':
            line.append(token)
        else:  # End of line, compile
            if len(line) == 0:  # Blank line, special handling
                indent = indents[-1]
                if indent == -1:  # Leading blank line, can be ignored
                    line = []
                    continue
                _nodes = [TextNode('')]
            else:
                indent = len(line[0].value)
                _nodes = compile_line(line[1:])
            _indents = [indent]*len(_nodes)
            while indent <= indents[-1]:
                indents.pop()
                node = nodes.pop()
                nodes[-1].append(node)
            if not isinstance(nodes[-1], NodeChildren):
                raise CompilerError(f'node {nodes[-1]} does not support children')
            nodes.extend(_nodes)
            indents.extend(_indents)
            line = []
    while True:  # Final compression and return
        node = nodes.pop()
        if nodes:
            nodes[-1].append(node)
        else:
            return node

def compile_line(line):
    indicator, line = line[0].value, line[1:]
    for i, token in enumerate(line):
        if token.type == 'INLINE':
            line, inlineNodes = line[:i], compile_line(line[i+1:])
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
