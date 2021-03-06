'''
''''''
==================================== To-do ====================================
=== Bug-fixes ===

=== Implementation ===

=== Features ===
CallNode - applies the given function to its rendered lines (not! each line separately)
String interpolation should escape the inserted strings
LoadNode? - import libraries

=== Style ===
'''

from dataclasses import dataclass, field, replace, InitVar
from typing import Tuple, List, Dict, Optional, ClassVar
from .expression import Expression, String, VarList, VarDict, AttrDict

## Constants
__all__ = [
    'NodeChildren',
    'RootNode',
    'TextNode',
    'WyrmCommentNode',
    'HTMLCommentNode',
    'HTMLTagNode',
    'ExpressionNode',
    'IfNode',
    'ConditionNode',
    'ForNode',
    'LoopNode',
    'EmptyNode',
    'WithNode',
    'IncludeNode',
    'BlockNode',
    'RequireNode',
    'HTMLNode',
    'CSSNode',
    'JSNode',
    'MarkdownNode'
]

## Exceptions
class TokenError(Exception):
    pass

class NodeError(Exception):
    pass

class TemplateError(Exception):
    pass

## Nodes
@dataclass
class Node:
    @classmethod
    def str(cls):
        return cls.__name__

    def append(self, value):
        raise NodeError(f'{self!s} cannot take children')

    def extend(self, value):
        raise NodeError(f'{self!s} cannot take children')

    @classmethod
    def make(cls, line):
        return cls()

    def render(self, *contexts):
        yield from ()

@dataclass
class NodeChildren(Node):
    children: List[Node] = field(default_factory=list, init=False)

    def __len__(self):
        return len(self.children)

    def __getitem__(self, key):
        return self.children[key]

    def __setitem__(self, key, value):
        if isinstance(value, Node):
            self.children[key] = value
        else:
            raise NodeError('nodes may only have nodes as children')

    def __delitem__(self, key):
        del self.children[key]

    def __iter__(self):
        yield from self.children

    def __reversed__(self):
        reversed(self.children)

    def __contains__(self, value):
        return value in self.children

    def append(self, value):
        if isinstance(value, Node):
            self.children.append(value)
        else:
            raise NodeError('nodes may only have nodes as children')

    def extend(self, value):
        if all(isinstance(node, Node) for node in value):
            self.children.extend(value)
        else:
            raise NodeError('nodes may only have nodes as children')

    def render(self, *contexts):
        for child in self:
            yield from child.render(*contexts)

class NodeChildrenIndent(NodeChildren):
    def render(self, *contexts):
        indentlength = contexts[-1].get('_indentlength', 4)
        for line in super().render(*contexts):
            line.indent += indentlength
            yield line

@dataclass
class RootNode(NodeChildren):
    def render(self, *contexts):
        if not contexts:
            contexts = ({},)  # Not sure if I want to set the global context here directly or not
        super().render(self, *contexts)

# Text nodes
@dataclass
class TextNode(Node):
    text: String = String('')

    @staticmethod
    def make(line):
        if len(line) == 0:
            return TextNode()
        elif len(line) == 1:
            return TextNode(text=String(line[0].value))
        else:
            raise TemplateError('text nodes can only take a single token')

    def render(self, *contexts):
        yield Line(self.text.evaluate(*contexts))

@dataclass
class CommentNode(NodeChildrenIndent):
    comment: String = String('')

    def append(self, value):
        if self.comment.string:
            raise NodeError('comment nodes may not have children if they have a comment string')
        else:
            super().append(value)

    def extend(self, value):
        if self.comment.string:
            raise NodeError('comment nodes may not have children if they have a comment string')
        else:
            super().extend(value)

    @classmethod
    def make(cls, line):
        if not line:
            return cls()
        if len(line) != 1:
            raise TemplateError('comment nodes can only take a single token')
        return cls(comment=String(line[0].value))

@dataclass
class WyrmCommentNode(CommentNode):
    def render(self, *contexts):
        yield from ()

@dataclass
class HTMLCommentNode(CommentNode):
    def render(self, *contexts):
        if self.comment:
            yield Line(f'<!-- {self.comment.evaluate(*contexts)} -->')
        else:
            yield Line('<!--')
            yield from super().render(*contexts)
            yield Line('-->')

@dataclass
class HTMLTagNode(NodeChildrenIndent):
    name: str
    attributes: AttrDict

    @staticmethod
    def make(line):
        from .htmltag import make as makeTag
        name, attributes = makeTag(line)
        return HTMLTagNode(name=name, attributes=attributes)

    def render(self, *contexts):
        from .htmltag import render as renderTag
        open, close = renderTag(self.name, self.attributes, *contexts)
        contents = list(super().render(*contexts))
        blankline = (contents and not contents[-1].text)  # Blank line
        if blankline:
            contents.pop()
        if close is None:  # Self-closing tag
            if contents:  # Tag isn't empty
                raise NodeError('self-closing HTML tags may not have children')
            yield Line(open)
        elif len(contents) == 0:
            yield Line(open + close)
        elif len(contents) == 1:
            yield Line(open + contents[0].text + close)
        else:
            yield Line(open)
            yield from contents
            yield Line(close)
        if blankline:
            yield Line('')

@dataclass
class ExpressionNode(Node):
    expr: Expression

    @staticmethod
    def make(line):
        return ExpressionNode(expr=Expression.make(line))

    def render(self, *contexts):
        expr = str(self.expr.evaluate(*contexts))
        if expr:
            yield Line(expr)

# Control nodes
@dataclass
class IfNode(NodeChildren):
    def render(self, *contexts):
        for child in self:
            if child:
                yield from child.render(*contexts)
                break

@dataclass
class ConditionNode(NodeChildren):
    condition: Expression

    def __bool__(self):
        return self.condition.evaluate(*contexts)

    @staticmethod
    def make(line):
        from .expression import Boolean
        if not line:
            return ConditionNode(condition=Boolean(True))
        else:
            return ConditionNode(condition=Expression.make(line))

@dataclass
class ForNode(NodeChildren):
    vars: VarList
    container: Expression

    @staticmethod
    def make(line):
        for ix, token in enumerate(line):
            if token.type == 'OPERATOR' and token.value == 'in':
                break  # This leaves `ix` as the index of the `in` token
        else:
            raise NodeError('`for` requires the keyword `in`')
        vars = VarList.make(line[:ix])
        container = Expression.make(line[ix+1:])
        return ForNode(vars=vars, container=container)

    def render(self, *contexts):
        container = self.container.evaluate(*contexts)
        loop = empty = else_ = None
        for i, child in enumerate(self):
            if i==0 and isinstance(child, LoopNode):
                loop = child
            elif isinstance(child, EmptyNode):
                empty = child
            elif isinstance(child, ConditionNode):
                else_ = child
        assert loop is not None
        if container:
            length = len(container)
            if contexts and 'loop' in contexts[-1]:
                parent = contexts[-1]['loop']
            else:
                parent = None
            vars = self.vars
            for i, item in enumerate(container):
                if len(vars) == 1:
                    context = {vars[0], item}
                else:
                    context = dict(zip(vars, item))
                context['loop'] = LoopVars(i, length, parent)
                yield from loop.render(context, *contexts)
            if else_ is not None:
                yield from else_.render(*contexts)
        elif empty is not None:
            yield from empty.render(*contexts)

@dataclass
class LoopNode(NodeChildren):
    pass

@dataclass
class EmptyNode(NodeChildren):
    pass

@dataclass
class WithNode(NodeChildren):
    vars: VarDict
    limitcontext: bool

    @staticmethod
    def make(line):
        if line and line[0].type == 'KEYWORD' and line[0].value == 'only':
            line = line[1:]
            limitcontext = True
        else:
            limitcontext = False
        vars = VarDict.make(line)
        return WithNode(vars=vars, limitcontext=limitcontext)

    def render(self, *contexts):
        context = self.vars.evaluate(*contexts)
        if self.limitcontext:
            yield from super().render(context, contexts[-1])
        else:
            yield from super().render(context, *contexts)

# Command nodes
@dataclass
class IncludeNode(NodeChildren):
    file: Expression
    vars: VarDict
    limitcontext: bool

    @staticmethod
    def make(line):
        for ix, token in enumerate(line):
            if token.type == 'KEYWORD' and token.value == 'with':
                break  # This leaves `ix` as the index of the `with` token
        else:
            ix = None
        file = Expression.make(line[:ix])
        if ix is None:
            return IncludeNode(file=file)
        else:
            with_ = WithNode.make(line[ix+1:])
            return IncludeNode(file=file, vars=with_.vars, limitcontext=with_.limitcontext)

    def render(self, *contexts):
        from .template import load_template
        template = load_template(self.file.evaluate(*contexts))  # Temporary call
        context = self.vars.evaluate(*contexts)
        _blocks = {}
        for block in self:
            _blocks[block.name] = block.render(*contexts)
        context['_blocks'] = _blocks
        if self.limitcontext:
            yield from template.render(context, contexts[-1])
        else:
            yield from template.render(context, *contexts)

@dataclass
class BlockNode(NodeChildren):
    name: str

    @staticmethod
    def make(line):
        if line[0].type == 'IDENTIFIER':
            return BlockNode(name=line[0].value)
        else:
            raise NodeError('block nodes take a single unquoted string')

    def render(self, *contexts):
        for context in contexts:
            if '_blocks' in context:
                _blocks = context['_blocks']
                if self.name in _blocks:
                    yield from _blocks[self.name]
                    return
        yield from super().render(*contexts)

@dataclass
class RequireNode(Node):
    vars: VarList

    @staticmethod
    def make(line):
        vars = VarList.make(line)
        return RequireNode(vars=vars)

    def render(self, *contexts):
        for var in self.vars:
            for context in contexts:
                if var in context:
                    break
            else:
                raise TemplateError(f'variable not in context: {var!r}')
        yield from ()

@dataclass
class HTMLNode(HTMLTagNode):
    name: ClassVar[str] = 'html'
    doctype: str

    @staticmethod
    def make(line):
        from .htmltag import makeAttributes
        if line and line[0].type == 'NUMBER':
            doctype, ix = line[0].value, 1
            if line[1].type == 'IDENTIFIER' and line[1].value in ('strict', 'transitional', 'frameset'):
                doctype, ix = ' '.join(doctype, line[1].value), 2
            elif doctype in ('1', '4'):
                doctype = ' '.join(doctype, 'strict')
        else:
            doctype, ix = '', 0
        attributes = makeAttributes(line[ix:])
        return HTMLNode(doctype=doctype, attributes=attributes)

    def render(self, *contexts):
        from .htmltag import DOCTYPES
        doctype = self.doctype or contexts[-1].get('_doctype', '5')
        yield Line(DOCTYPES[doctype])
        yield from super().render(*contexts)

@dataclass
class ResourceNode(NodeChildren):
    src: Optional[Expression]

    def append(self, value):
        if self.src is not None:
            raise NodeError('resource nodes may not have children if they have a source expression')
        else:
            super().append(value)

    def extend(self, value):
        if self.src is not None:
            raise NodeError('resource nodes may not have children if they have a source expression')
        else:
            super().extend(value)

    @classmethod
    def make(cls, line):
        if line:
            return cls(src=Expression.make(line))
        else:
            return cls(src=None)

@dataclass
class TagResourceNode(ResourceNode, HTMLTagNode):
    name: ClassVar[str]
    attributes: ClassVar[AttrDict] = AttrDict([])
    sourcetag: ClassVar[str]

    def render(self, *contexts):
        from .htmltag import render as renderTag
        if self.src is None:
            yield from super().render(*contexts)
        else:
            yield Line(self.sourcetag.format(self.src.evaluate(*contexts)))

@dataclass
class CSSNode(TagResourceNode):
    name = 'style'
    sourcetag = '<link rel="stylesheet" type="text/css" href="{}.css">'

@dataclass
class JSNode(TagResourceNode):
    name = 'script'
    sourcetag = '<script src="{}.js">'

@dataclass
class MarkdownNode(ResourceNode):
    def render(self, *contexts):
        from .template import load_file
        if self.src is None:
            string = '\n'.join(line.text for line in super().render(*contexts))
        else:
            string = load_file(self.src.evaluate(*contexts), '.md')
        yield from markdown(string).splitlines()

## Helper Classes
@dataclass
class Line:
    text: str = ''
    indent: int = 0

    def __str__(self):
        return f'{' '*self.indent}{self.text}'

@dataclass
class LoopVars:
    length: InitVar[int]
    counter: int
    counter1: int = field(init=False)
    revcounter: int = field(init=False)
    revcounter1: int = field(init=False)
    first: bool = field(init=False)
    last: bool = field(init=False)
    parent: Optional['LoopVars'] = None

    def __post_init__(self, length):
        self.counter1 = self.counter + 1
        self.revcounter = length - self.counter1
        self.revcounter1 = length - self.counter
        self.first = self.counter == 0
        self.last = self.revcounter == 0

## Helper Functions
# Temp
def markdown(string):
    return string
