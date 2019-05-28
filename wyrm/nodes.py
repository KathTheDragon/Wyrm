from dataclasses import dataclass, field, replace, InitVar
from typing import Tuple, List, Dict, Optional
from .expression import Expression, String

## Constants
__all__ = ['NodeChildren', 'RootNode', 'TextNode', 'CommentNode', 'HTMLCommentNode', 'HTMLTagNode', 'ExpressionNode', 'IfNode', 'ConditionNode', 'ForNode', 'LoopNode', 'EmptyNode', 'WithNode', 'IncludeNode', 'BlockNode', 'RequireNode']

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
    def append(self, value):
        raise NodeError('node cannot take children')

    def extend(self, value):
        raise NodeError('node cannot take children')

    @classmethod
    def make(cls, line):
        return cls()

    def render(self, *contexts):
        return []

@dataclass
class NodeChildren(Node):
    children: List[Node] = field(default_factory=list)

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
        iter(self.children)

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
            lines.extend([(' '*4 + line) for line in child.render(*contexts)])
        return lines

@dataclass
class RootNode(NodeChildren):
    pass

# Text nodes
@dataclass
class TextNode(Node):
    text: String = String()

    @classmethod
    def make(cls, line):
        return cls(text=String(line[0].value))

    def render(self, *contexts):
        return [self.text.evaluate(*contexts)]

@dataclass
class CommentNode(TextNode):
    def render(self, *contexts):
        return []

@dataclass
class HTMLCommentNode(TextNode):
    def render(self, *contexts):
        return ['<!--'] + super().render(*contexts) + ['-->']

@dataclass
class HTMLTagNode(NodeChildren):
    name: str = ''
    attributes: dict = field(default_factory=dict)

    @staticmethod
    def make(line):
        from .htmltag import make as makeTag
        name, attributes = makeTag(line)
        return HTMLTagNode(name=name, attributes=attributes)

    def render(self, *contexts):
        from .htmltag import render as renderTag
        open, close = renderTag(self.name, self.attributes, *contexts)
        if close is None:  # Self-closing tag
            return [open]
        else:
            return [open] + super().render(*contexts) + [close]

@dataclass
class ExpressionNode(Node):
    expr: Expression = Expression()

    @staticmethod
    def make(line):
        return ExpressionNode(expr=Expression.make(line))

    def render(self, *contexts):
        return [self.expr.evaluate(*contexts)]

# Control nodes
@dataclass
class IfNode(NodeChildren):
    def render(self, *contexts):
        for child in self:
            lines = child.render(*contexts)
            if lines:
                return lines
        return []

@dataclass
class ConditionNode(NodeChildren):
    condition: Expression = Expression()

    @staticmethod
    def make(line):
        if not line:
            return ConditionNode(condition=Expression(True))
        else:
            return ConditionNode(condition=Expression.make(line))

    def render(self, *contexts):
        if self.condition.evaluate(*contexts):
            return super().render(*contexts)
        else:
            return []

@dataclass
class ForNode(NodeChildren):
    vars: Tuple[str] = ()
    container: Expression = ''

    @staticmethod
    def make(line):
        from .expression import ArgList
        for ix, token in enumerate(line):
            if token.type == 'IDENTIFIER' and token.value == 'in':
                break  # This leaves `ix` as the index of the `in` token
        else:
            raise NodeError('`for` requires the keyword `in`')
        vars = ArgList.make(line[:ix])
        if vars.kwargs:
            raise NodeError('`for` cannot take keyword variables in the variable list')
        container = Expression.make(line[ix+1:])
        return ForNode(vars=vars.args, container=container)

    def render(self, *contexts):
        lines = []
        container = self.container.evaluate(*contexts)
        loop = empty = else_ = None
        for child in self:
            if isinstance(child, LoopNode):
                loop = child
            elif isinstance(child, EmptyNode):
                empty = child
            elif isinstance(child, ConditionNode):
                else_ = child
        if container:
            length = len(container)
            if 'loop' in contexts[-1]:
                parent = contexts[-1]['loop']
            else:
                parent = None
            for i, item in enumerate(container):
                context = dict(zip(self.vars, item))
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
    vars: Dict[str, Expression] = field(default_factory=dict)
    limit_context: bool = False

    @staticmethod
    def make(line):
        from .expression import ArgList
        if line and line[0].type == 'IDENTIFIER' and line[0].value == 'only':
            line = line[1:]
            limit_context = True
        else:
            limit_context = False
        vars = ArgList.make(line)
        if vars.args:
            raise NodeError('`with` takes only keyword variables')
        return WithNode(vars=vars.kwargs, limit_context=limit_context)

    def render(self, *contexts):
        context = {var: expr.evaluate(*contexts) for var, expr in self.vars.items()}
        if self.limit_context:
            return super().render(context)
        else:
            return super().render(context, *contexts)

# Command nodes
@dataclass
class IncludeNode(NodeChildren):
    file: Expression = Expression()
    vars: Dict[str, Expression] = field(default_factory=dict)
    limit_context: bool = False

    @staticmethod
    def make(line):
        from .expression import ArgList
        for ix, token in enumerate(line):
            if token.type == 'IDENTIFIER' and token.value == 'with':
                break  # This leaves `ix` as the index of the `with` token
        else:
            ix = None
        file = Expression.make(line[:ix])
        if ix is None:
            return IncludeNode(file=file)
        else:
            try:
                with_ = WithNode.make(line[ix+1:])
            except NodeError:
                raise NodeError('`include` takes only keyword variables')
            return IncludeNode(file=file, vars=with_.vars, limit_context=with_.limit_context)

    def render(self, *contexts):
        from .template import load_template
        template = load_template(self.file.evaluate(*contexts))  # Temporary call
        context = {var: expr.evaluate(*contexts) for var, expr in self.vars.items()}
        _blocks = {}
        for block in self:
            _blocks[block.name] = block.render(*contexts)
        context['_blocks'] = _blocks
        if self.limit_context:
            return template.render(context)
        else:
            return template.render(context, *contexts)

@dataclass
class BlockNode(NodeChildren):
    name: str = ''

    @staticmethod
    def make(line):
        if line[0].type == 'IDENTIFIER':
            return BlockNode(line[0].value)

    def render(self, *contexts):
        for context in contexts:
            if '_blocks' in context:
                _blocks = context['_blocks']
                if self.name in blocks:
                    return _blocks[self.name]
        return super().render(*contexts)

@dataclass
class RequireNode(Node):
    vars: Tuple[str] = ()

    @staticmethod
    def make(line):
        from .expression import ArgList
        vars = ArgList.make(line)
        if vars.kwargs:
            raise NodeError('`require` cannot take keyword variables')
        return RequireNode(vars.args)

    def render(self, *contexts):
        for var in self.vars:
            for context in contexts:
                if var in context:
                    break
            else:
                raise TemplateError(f'variable not in context: {var!r}')
        return []

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
