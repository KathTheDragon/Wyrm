import re
from dataclasses import dataclass

## Constants
STRING = r'([^\\\n]|\\.)*?'
TOKENS = {
    'INDENT': r'^ *',
    'WHITESPACE': r' +',
    'NEWLINE': r'\n',
    'OPERATOR': r'[-+@&|^~#.]|[<>!=]?=|[*/<>]{1,2}',
    'SEPARATOR': r'[,:]',
    'LBRACKET': r'[([{]',
    'RBRACKET': r'[}\])]',
    'IDENTIFIER': r'[a-zA-Z_]\w*',
    'STRING': fr'\'{STRING}\'|\"{STRING}\"',
    'NUMBER': r'\d+\.?\d*|\.\d+',
    'UNKNOWN': r'.'
}
TOKEN_REGEX = re.compile('|'.join(f'(?P<{type}>{regex})' for type, regex in TOKENS.items()), flags=re.M)
WHITESPACE_REGEX = re.compile(TOKENS['WHITESPACE'])
INDICATOR_REGEX = re.compile(r'(?P<INDICATOR>([/%\-=:]|/!)? ?)')
TEXT_REGEX = re.compile(fr'(?P<TEXT>{STRING}$)', flags=re.M)

## Exceptions
class CompilerError(Exception):
    pass

## Classes
@dataclass
class Token:
    type: str
    value: str
    line: int
    col: int

## Functions
def tokenise_string(string):
    brackets = []
    ix = 0
    line_num = 1
    line_start = 0
    text_indent = None
    last_token = None
    len_string = len(string)
    while ix < len_string:
        match = None
        column = ix-line_start
        regex = TOKEN_REGEX
        if last_token is not None:
            if last_token.type in ('INDENT', 'INLINE'):
                regex = INDICATOR_REGEX
            elif last_token.type == 'INDICATOR' and last_token.value in ('', '/', '/!'):
                regex = TEXT_REGEX
        match = regex.match(string, ix)
        type = match.lastgroup
        value = match.group()
        if type == 'INDENT':
            if text_indent is not None:
                if len(value) > len(text_indent):
                    value = text_indent
                else:
                    text_indent = None
        ix += len(value)
        if type in ('INDICATOR', 'SEPARATOR'):
            value = value.strip()
        if type == 'INDICATOR' and last_token.type == 'INDENT' and value == '':
            text_indent = last_token.value
        elif type == 'SEPARATOR' and value == ':':
            if not brackets:
                type = 'INLINE'
                _match = WHITESPACE_REGEX.match(string, ix+1)
                if _match is not None:
                    ix += len(_match.group())
        elif type == 'LBRACKET':
            brackets.append(value)
        elif type == 'RBRACKET':
            if not brackets:
                raise CompilerError(f'unmatched bracket: `{value}` @ {line_num}:{column}')
            bracket = brackets.pop()
            if bracket+value not in ('()', '[]', '{}'):
                raise CompilerError(f'mismatched brackets: `{value}` @ {line_num}:{column}')
        elif type == 'IDENTIFIER':
            pass  # Might do something later with converting these to more specific tokens, like keywords, tag names, etc.
        elif type == 'WHITESPACE':
            continue
        elif type == 'UNKNOWN':
            raise CompilerError(f'unknown character: `{value}` @ {line_num}:{column}')
        last_token = Token(type, value, line_num, column)
        yield last_token
        if type == 'NEWLINE':
            line_num += 1
            line_start = ix

def compile_tokens(tokens):
    # Make the lines
    lines = [[]]
    for token in tokens:
        if token.type == 'NEWLINE':
            lines.append([])
            continue
        lines[-1].append(token)
    if lines[-1]:
        lines.append([])  # Ensure we end with an empty list
    # Compile the lines
    indents = [-1]
    nodes = [RootNode()]
    for line in lines:
        if len(line) == 0:  # End of template
            indent = 0
            _nodes = []
        elif len(line) == 2:  # Blank line, special handling
            indent = indents[-1]
            _nodes = [TextNode()]
        else:
            indent = len(line[0].value)
            _nodes = compile_line(line[1:])
        while indent < indents[-1]:
            indents.pop()
            node = nodes.pop()
            nodes[-1].append(node)
        if indent == indents[-1]:
            node = nodes.pop()
            nodes[-1].append(node)
        elif not isinstance(nodes[-1], NodeChildren):
            raise CompilerError(f'node {nodes[-1]} does not support children')
        nodes.extend(_nodes)
    return nodes[0]

def compile_line(line):
    from .nodes import *
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
    node = {
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
    }[key].make(line)
    if key == 'if':
        nodes = [IfNode(), node]
    elif key == 'for':
        nodes = [node, LoopNode()]
    else:
        nodes = [node]
    nodes.extend(inlineNodes)
    return nodes
