import re
from .expression import Expression

## Constants
TOKENS = {
    'TAGNAME': r'^[a-zA-Z_][-\w]*',
    'ID_SHORTCUT': r' *#[a-zA-Z][-\w]*',
    'CLASS_SHORTCUT': r' *\.[a-zA-Z][-\w]*',
    'UNKNOWN': r'.'
}
TOKEN_REGEX = re.compile('|'.join(f'(?P<{type}>{regex})' for type, regex in TOKENS.items()), flags=re.M)
DOCTYPES = {
    '5': '<!doctype html>',
    '4 strict': '<!doctype html PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">',
    '4 transitional': '<!doctype html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">',
    '4 frameset': '<!doctype html PUBLIC "-//W3C//DTD HTML 4.01 Frameset//EN" "http://www.w3.org/TR/html4/frameset.dtd">',
    '1 strict': '<!doctype html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">',
    '1 transitional': '<!doctype html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">',
    '1 frameset': '<!doctype html PUBLIC "-//W3C//DTD XHTML 1.0 Frameset//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-frameset.dtd">',
    '1.1': '<!doctype html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">',
}
SELF_CLOSING = [
    'area',
    'base',
    'br',
    'col',
    'command',
    'embed',
    'keygen',
    'hr',
    'img',
    'input',
    'link',
    'meta',
    'param',
    'source',
    'track',
    'wbr'
]

## Functions
def tokenise(string, linenum=0, colstart=0):
    from .compiler import Token
    from .expression import tokenise as tokenise_expression
    for match in TOKEN_REGEX.finditer(string):
        type = match.lastgroup
        value = match.group()
        column = match.start() + colstart
        if type == 'ID_SHORTCUT':
            value = value.lstrip(' #')
        elif type == 'CLASS_SHORTCUT':
            value = value.lstrip(' .')
        elif type == 'UNKNOWN':
            break
        yield Token(type, value, linenum, column)
    else:
        yield Token('END', '', linenum, match.end()+colstart)
        return
    yield from tokenise_expression(string[match.start():], linenum, match.start()+colstart)

def make(line):
    # Get tag name
    _line = line  # Just in case we need to undo
    name, line = popHTMLIdentifier(line)
    if line[0].value == '=':
        name, line = '', _line
    if not name:
        name = 'div'
    # Get id/class shortcuts
    id = ''
    classes = []
    while line[0].value in ('#', '.'):
        type = line[0].value
        value, line = popHTMLIdentifier(line[1:])
        if type == '#':
            id = value
        else:
            classes.append(value)
    # Get attributes
    attributes = makeAttributes(line)
    if id:
        attributes['id'] = id
    if classes:
        if 'class' in attributes:
            attributes['class'] = ' '.join([attributes['class']] + classes)
        else:
            attributes['class'] = ' '.join(classes)
    return name, attributes

def makeAttributes(line):
    attributes = {}
    while line:
        attr, line = popHTMLIdentifier(line)
        if line[0].value == '=':
            expr, line = Expression.pop(line)
        else:
            expr = Expression(True)
        attributes[attr] = expr
    return attributes

def popHTMLIdentifier(line):
    if line[0].type != 'IDENTIFIER':
        return '', line
    for i, token in enumerate(line):
        if token.type == 'IDENTIFIER' and (i == 0 or line[i-1].value == '-'):
            continue
        elif token.value == '-' and line[i-1].type == 'IDENTIFIER':
            continue
        break
    else:
        return ''.join(token.value for token in line), []
    return ''.join(token.value for token in line[:i]), line[i:]

def render(name, attributes, *contexts):
    for attr, expr in attributes.items():
        attributes[attr] = expr.evaluate(*contexts)
    attrList = [(f'{attr}={value!r}' if value is not True else attr) for attr, value in attributes.items() if value]
    if attrList:
        open = f'{name} {" ".join(attrList)}'
    else:
        open = name
    if name in SELF_CLOSING:  # This may be a config option
        return f'<{open} />', None
    else:
        return f'<{open}>', f'</{name}>'
