import re
from dataclasses import dataclass

## Constants
TOKENS = {
    'INDENT': r'^ *(?!$| )',
    'OPERATOR': r'[#.^~]|[+\-=!%@&|]=?|[*/<>]{1,2}=?',
    'SEPARATOR': r'[,:] ?',
    'LBRACKET': r'[([{]',
    'RBRACKET': r'[}\])]',
    'IDENTIFIER': r'[a-zA-Z_]\w*',
    'STRING': r'\".*?[^\\]\"|\'.*?[^\\]\'|[\'\"]{2}',
    'NUMBER': r'\d+\.?\d*',
    'WHITESPACE': r' +',
    'NEWLINE': r'\n',
    'UNKNOWN': r'.'
}
TOKEN_REGEX = re.compile('|'.join(f'(?P<{type}>{regex})' for type, regex in TOKENS.items()), flags=re.M)
INDICATOR_REGEX = re.compile(r'(?P<INDICATOR>([/%\-=:]|/!)? ?)')
TEXT_REGEX = re.compile(r'(?P<TEXT>.*$)', flags=re.M)

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
def tokenise(string):
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
        elif type == 'UNKNOWN':
            raise CompilerError(f'unknown character: `{value}` @ {line_num}:{column}')
        token = Token(type, value, line_num, column)
        yield token
        if type == 'NEWLINE':
            line_num += 1
            line_start = ix
        last_token = token
