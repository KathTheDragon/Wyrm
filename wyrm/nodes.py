from dataclasses import dataclass, field, replace, InitVar
from typing import Tuple, List, Optional

## Constants
__all__ = ['RootNode', 'TextNode', 'CommentNode', 'HTMLCommentNode', 'HTMLTagNode', 'ExpressionNode', 'IfNode', 'ConditionNode', 'ForNode', 'LoopNode', 'EmptyNode', 'DefinitionNode', 'IncludeNode', 'BlockNode', 'RequireNode']

## Exceptions
class NodeError(Exception):
    pass

class TemplateError(Exception):
    pass

## Nodes
@dataclass
class Node:
    __slots__ = ()

    def render(self, *contexts):
        return []

    def replace_blocks(self, blocks):
        pass

@dataclass
class NodeChildren(Node):
    children: List[Node] = field(default_factory=list)  # I'd like to be able to remove this default so I can use __slots__ on all subclasses

    def __len__(self):
        return len(self.children)

    def __getitem__(self, key):
        return self.children[key]

    def __setitem__(self, key, value):
        self.children[key] = value

    def __delitem__(self, key):
        del self.children[key]

    def __iter__(self):
        iter(self.children)

    def __reversed__(self):
        reversed(self.children)

    def __contains__(self, value):
        return value in self.children

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
        from expression import String
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
        from htmltag import render
        open, close = render(self.name, self.attributes, *contexts)
        if close is None:  # Self-closing tag
            return [open]
        else:
            return [open] + super().render(*contexts) + [close]

@dataclass
class ExpressionNode(Node):
    value: str = ''

    def render(self, *contexts):
        from expression import evaluate
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
        from expression import evaluate
        if evaluate(self.condition, *contexts):
            return super().render(*contexts)
        else:
            return []

@dataclass
class ForNode(NodeChildren):
    vars: Tuple[str] = ()
    container: str = ''

    def render(self, *contexts):
        from expression import evaluate
        lines = []
        container = evaluate(self.container, *contexts)
        if isinstance(self[0], Loop):
            loop = self[0]
        else:
            raise NodeError('for node must have a loop node as its first child')
        if isinstance(self[-1], Empty):
            empty = self[-1]
        else:
            empty = None
        if container:
            length = len(container)
            if 'loop' in contexts[-1]:
                parent = contexts[-1]['loop']
            else:
                parent = None
            for i, item in enumerate(container):
                context = dict(zip(self.vars, item))
                context['loop'] = LoopVars(i, length, parent)
                lines.extend(self[0].render(*contexts, context))
        elif empty is not None:
            return empty.render(*contexts)
        return lines

@dataclass
class LoopNode(NodeChildren):
    __slots__ = ()

@dataclass
class EmptyNode(NodeChildren):
    __slots__ = ()

# Do I need this?
@dataclass
class DefinitionNode(Node):
    name: str = ''
    value: str = ''

    def render(self, *contexts):
        from expression import evaluate
        value = evaluate(self.value, *contexts)
        contexts[0][self.name] = value
        return []

# Command nodes
@dataclass
class IncludeNode(NodeChildren):
    filename: str = ''

    def render(self, *contexts):
        pass  # Will come back to this, this is complex and needs a lot of infrastructure
        # This works as follows:
        # - loads the specified template
        # - recursively searches the included template for Block and Include nodes
        # -- for each Block node found, it checks the block's name, and if that's the name of a child block of this Include node, replaces the block in the included template with the child node
        # -- for each Include node found, repeat this process. The blocks used are not only the children of the original Include, but each new Include encountered down the chain
        # - once the inclusions and blocks are fully evaluated, the included template is rendered, and the result returned
        # In particular, this cannot call .render on the included nodes until the final step

@dataclass
class BlockNode(NodeChildren):
    name: str = ''

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
