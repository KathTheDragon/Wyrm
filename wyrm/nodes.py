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
        return []

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
        lines = []
        for child in self:
            lines.extend(child.render(*contexts))
        return lines

class NodeChildrenIndent(NodeChildren):
    def render(self, *contexts):
        lines = []
        for child in self:
            lines.extend([(' '*4 + line) for line in child.render(*contexts)])
        return lines

@dataclass
class RootNode(NodeChildren):
    pass

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
        return [self.text.evaluate(*contexts)]

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
        return []

@dataclass
class HTMLCommentNode(CommentNode):
    def render(self, *contexts):
        if self.comment:
            return [f'<!-- {self.comment.evaluate(*contexts)} -->']
        else:
            return ['<!--'] + super().render(*contexts) + ['-->']

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
        contents = super().render(*contexts)
        if close is None:  # Self-closing tag
            if contents:  # Tag isn't empty
                raise NodeError('self-closing HTML tags may not have children')
            return [open]
        elif len(contents) == 0:
            return [open + close]
        elif contents[-1] == ' '*4:  # Blank line
            if len(contents) == 1:
                return [open + close, '']
            elif len(contents) == 2:
                return [open + contents[0][4:] + close, '']
            else:
                return [open] + contents[:-1] + [close, '']
        elif len(contents) == 1:
            return [open + contents[0][4:] + close]
        else:
            return [open] + contents + [close]

@dataclass
class ExpressionNode(Node):
    expr: Expression

    @staticmethod
    def make(line):
        return ExpressionNode(expr=Expression.make(line))

    def render(self, *contexts):
        expr = str(self.expr.evaluate(*contexts))
        if expr:
            return [expr]
        else:
            return []

# Control nodes
@dataclass
class IfNode(NodeChildren):
    def render(self, *contexts):
        for child in self:
            lines = child.render(*contexts)
            if isinstance(lines, list):
                return lines
        return []

@dataclass
class ConditionNode(NodeChildren):
    condition: Expression

    @staticmethod
    def make(line):
        from .expression import Boolean
        if not line:
            return ConditionNode(condition=Boolean(True))
        else:
            return ConditionNode(condition=Expression.make(line))

    def render(self, *contexts):
        if self.condition.evaluate(*contexts):
            return super().render(*contexts)
        else:
            return ()

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
        lines = []
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
                lines.extend(loop.render(context, *contexts))
            if else_ is not None:
                lines.extend(else_.render(*contexts))
        elif empty is not None:
            return empty.render(*contexts)
        return lines

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
            return super().render(context)
        else:
            return super().render(context, *contexts)

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
            return template.render(context)
        else:
            return template.render(context, *contexts)

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
                if self.name in blocks:
                    return _blocks[self.name]
        return super().render(*contexts)

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
        return []

@dataclass
class HTMLNode(HTMLTagNode):
    name: str = field(default='html', init=False, repr=False)
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
            doctype, ix = '5', 0  # To outsource to the config
        attributes = makeAttributes(line[ix:])
        return HTMLNode(doctype=doctype, attributes=attributes)

    def render(self, *contexts):
        from .htmltag import DOCTYPES
        return [DOCTYPES[self.doctype]] + super().render(*contexts)

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
class TagResourceNode(ResourceNode):
    tagname: ClassVar[str]
    sourcetag: ClassVar[str]

    def render(self, *contexts):
        from .htmltag import render as renderTag
        if self.src is None:
            lines = []
            for child in self:
                lines.extend([(' '*4 + line) for line in child.render(*contexts)])
            open, close = renderTag(self.tagname, AttrDict([]))
            return [open] + lines + [close]
        else:
            return [self.sourcetag.format(self.src.evaluate(*contexts))]

@dataclass
class CSSNode(TagResourceNode):
    tagname = 'style'
    sourcetag = '<link rel="stylesheet" type="text/css" href="{}.css">'

@dataclass
class JSNode(TagResourceNode):
    tagname = 'script'
    sourcetag = '<script src="{}.js">'

@dataclass
class MarkdownNode(ResourceNode):
    def render(self, *contexts):
        from .template import load_file
        if self.src is None:
            string = '\n'.join(super().render(*contexts))
        else:
            string = load_file(self.src.evaluate(*contexts), '.md')
        return markdown(string).splitlines()

## Helper Classes
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
