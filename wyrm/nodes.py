from dataclasses import dataclass, field, replace, InitVar
from typing import Tuple, List, Dict, Optional

## Constants
__all__ = ['NodeChildren', 'RootNode', 'TextNode', 'CommentNode', 'HTMLCommentNode', 'HTMLTagNode', 'ExpressionNode', 'IfNode', 'ConditionNode', 'ForNode', 'LoopNode', 'EmptyNode', 'WithNode', 'IncludeNode', 'BlockNode', 'RequireNode']

## Exceptions
class NodeError(Exception):
    pass

class TemplateError(Exception):
    pass

## Nodes
@dataclass
class Node:
    __slots__ = ()

    def append(self, value):
        raise NodeError('node cannot take children')

    def render(self, *contexts):
        return []

@dataclass
class NodeChildren(Node):
    children: List[Node] = field(default_factory=list)  # I'd like to be able to remove this default so I can use __slots__ on all subclasses

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

    def render(self, *contexts):
        lines = []
        for child in self:
            lines.extend([(' '*4 + line) for line in child.render(*contexts)])
        return lines

@dataclass
class RootNode(NodeChildren):
    __slots__ = ()

# Text nodes
@dataclass
class TextNode(Node):
    text: str = ''

    def render(self, *contexts):
        from .expression import String
        return [String(self.text).format(*contexts)]

@dataclass
class CommentNode(TextNode):
    __slots__ = ()

    def render(self, *contexts):
        return []

@dataclass
class HTMLCommentNode(TextNode):
    __slots__ = ()

    def render(self, *contexts):
        return ['<!--'] + super().render(*contexts) + ['-->']

@dataclass
class HTMLTagNode(NodeChildren):
    name: str = ''
    attributes: dict = field(default_factory=dict)

    def render(self, *contexts):
        from .htmltag import render as renderTag
        open, close = renderTag(self.name, self.attributes, *contexts)
        if close is None:  # Self-closing tag
            return [open]
        else:
            return [open] + super().render(*contexts) + [close]

@dataclass
class ExpressionNode(Node):
    value: str = ''

    def render(self, *contexts):
        from .expression import evaluate
        return [evaluate(self.value)]

# Control nodes
@dataclass
class IfNode(NodeChildren):
    __slots__ = ()

    def render(self, *contexts):
        for child in self:
            lines = child.render(*contexts)
            if lines:
                return lines
        return []

@dataclass
class ConditionNode(NodeChildren):
    condition: str = ''

    def render(self, *contexts):
        from .expression import evaluate
        if evaluate(self.condition, *contexts):
            return super().render(*contexts)
        else:
            return []

@dataclass
class ForNode(NodeChildren):
    vars: Tuple[str] = ()
    container: str = ''

    def render(self, *contexts):
        from .expression import evaluate
        lines = []
        container = evaluate(self.container, *contexts)
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
                lines.extend(loop.render(*contexts, context))
            if else_ is not None
                lines.extend(else_.render(*contexts))
        elif empty is not None:
            return empty.render(*contexts)
        return lines

@dataclass
class LoopNode(NodeChildren):
    __slots__ = ()

@dataclass
class EmptyNode(NodeChildren):
    __slots__ = ()

@dataclass
class WithNode(NodeChildren):
    vars: Dict[str, str] = field(default_factory=dict)

    def render(self, *contexts):
        from .expression import evaluate
        context = {var: evaluate(value, *contexts) for var, value in self.vars.items()}
        return super().render(*contexts, context)

# Command nodes
@dataclass
class IncludeNode(NodeChildren):
    filename: str = ''
    vars: Dict[str, str] = field(default_factory=dict)
    limit_context: bool = False

    def render(self, *contexts):
        from .template import load_template
        from .expression import evaluate
        template = load_template(filename)  # Temporary call
        context = {var: evaluate(value, *contexts) for var, value in self.vars.items()}
        _blocks = {}
        for block in self:
            name = block.name
            _blocks[name] = super(BlockNode, block).render(*contexts)
        context['_blocks'] = _blocks
        if limit_context:
            return template.render(context)
        else:
            return template.render(*contexts, context)

@dataclass
class BlockNode(NodeChildren):
    name: str = ''

    def render(self, *contexts):
        for context in contexts:
            if '_blocks' in context:
                blocks = context['_blocks']
                if self.name in blocks:
                    return blocks[self.name].render(*contexts)
        return super().render(*contexts)

@dataclass
class RequireNode(Node):
    vars: Tuple[str] = ()

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
    parent: Optional[LoopVars] = None

    def __post_init__(self, length):
        self.counter1 = self.counter + 1
        self.revcounter = length - self.counter1
        self.revcounter1 = length - self.counter
        self.first = self.counter == 0
        self.last = self.revcounter == 0
