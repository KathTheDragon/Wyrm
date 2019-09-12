import re
from .expression import Expression

## Constants
TOKENS = {
    'TAGNAME': r'^[a-zA-Z_][-\w]*',
    'ID_SHORTCUT': r' *#[a-zA-Z][-\w]*',
    'CLASS_SHORTCUT': r' *\.[a-zA-Z][-\w]*',
    'UNKNOWN': r'.'
}
TOKEN_REGEX = re.compile('|'.join(f'(?P<{type}>{regex})' for type, regex in TOKENS.items()))
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

## Exceptions
class ExpressionError(Exception):
    pass

## Functions
def tokenise(string, linenum=0, colstart=0):
    from .compiler import Token
    from .expression import tokenise as tokeniseExpression
    for match in TOKEN_REGEX.finditer(string, colstart):
        type = match.lastgroup
        value = match.group()
        column = match.start()
        if type == 'ID_SHORTCUT':
            value = value.lstrip(' #')
        elif type == 'CLASS_SHORTCUT':
            value = value.lstrip(' .')
        elif type == 'UNKNOWN':
            break
        yield Token(type, value, linenum, column)
    else:
        yield Token('END', '', linenum, match.end())
        return
    yield from tokeniseExpression(string, linenum, column)

def make(line):
    from .expression import String, ListLiteral
    line = list(line)
    # Get tag name
    if line[0].type == 'TAGNAME':
        name, line = line[0].value, line[1:]
    else:
        name = 'div'
    # Get id/class shortcuts
    id = ''
    classes = []
    for i, token in enumerate(line):
        if token.type == 'ID_SHORTCUT':
            id = token.value
        elif token.type == 'CLASS_SHORTCUT':
            classes.append(String(token.value))
        else:
            # Get attributes
            attributes = makeAttributes(line[i:])
            break
    else:
        attributes = makeAttributes([])
    if id:
        # id shortcut always overrides dynamic ids
        attributes.vars += (('id', String(id)),)
    if classes:
        attributes.vars += (('_class', ListLiteral(classes)),)
    return name, attributes

def makeAttributes(line):
    from .expression import AttrDict
    return AttrDict.make(line)

def render(name, attributes, *contexts):
    attributes = attributes.evaluate(*contexts)
    if '_class' in attributes:
        if 'class' in attributes:
            attributes['class'] = ' '.join([attributes['class']] + attributes['_class'])
        else:
            attributes['class'] = ' '.join(attributes['_class'])
        del attributes['_class']
    attrList = [(f'{attr}={value!r}' if value != True else attr) for attr, value in attributes.items() if value]
    if attrList:
        open = f'{name} {" ".join(attrList)}'
    else:
        open = name
    if name in SELF_CLOSING:  # This may be a config option
        return f'<{open} />', None
    else:
        return f'<{open}>', f'</{name}>'
