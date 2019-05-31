# Wyrm
Wyrm is a templating language that aims to be minimalistic while still being readable and simple to use. While it is oriented towards producing HTML documents, it can be used for any text-based document that needs to be generated dynamically.

## How to use
TBW

## Syntax example
```
:html 5 lang="en"
    % head
        % meta charset="utf-8"
        % meta name="viewport" content="width=device-width, initial-scale=1"
        % title: Wyrm Sample
        :css 'easy_css'
        :js
            alert('Embedded Javascript!')
    % body
        % h1: Examples
        % p: Inline the contents of tags, and other blocks.

        / Write comments that won't show up in the output
        /! And comments that will!

        Plaintext is easy to write, but if you need to start a line with a reserved character...
        \% You can escape it. %
        Text also supports interpolating {variables} with curly brackets.

        - if output
            Simple flow control
        - for feature in feature_list
            = feature
            Output variables directly
        - empty
            Easy looping as well
```
## Syntax Documentation

### Blocks
Wyrm uses indentation to define blocks, though the indentation level can be arbitrary, and can differ from block to block. All that matters is that all lines that are supposed to be in the same block have the same indentation. Both tabs and spaces can be used arbitrarily, but tabs are implicitly converted to spaces - by default, tabs are converted to 4 spaces, but this number can be set in the config.

### Line indicators
The punctuation characters `: - = / %`, as well as the two-character indicator `/!`, are used immediately after the indentation at the beginning of a line to mark six of the seven types of line explained below: commands, control code, output code, comments, HTML comments, and HTML tags. The seventh type, plaintext, is left unmarked. All line indicators may be optionally followed by a single space, to enhance readability. These punctuation characters are also used as line indicators in inlined blocks, explained below. These are the only two contexts that they are interpreted as line indicators.

### Plaintext
Any line that does not begin with one of the indicators is considered plaintext, and is mostly displayed without special modifications. Example:
```
This line displays exactly as written.
```
There are several exceptions to this generalisation.

Firstly, pairs of curly brackets `{...}` evaluate their contents as an expression, and interpolate the result. In order to display literal brackets, simply escape the opening bracket with a backslash: `\{`. An opening bracket without a closing bracket on the same line, however, never needs escaping. Examples:
```
This line displays the contents of the {variable}.
This line does \{not}.
Nor do these {lines
}.
```

The second exception is that when there are multiple consecutive lines of text, the lines all use the indentation of the first one, even if the subsequent lines are indented further. Any non-text line will reset this behaviour. If the first line also needs leading whitespace, simply begin that line with a backslash `\`:
```
This line has no leading whitespace.
    But this one has four spaces.
/ This comment interrupts the block of text
\    This line also starts with four spaces.
    So does this one.
        But this one starts with eight.
```
Such leading backslashes are removed before displaying the line, meaning that in order to begin a text line with one of the reserved punctuation marks, simply precede them with a backslash as well:
```
\= This line renders as literal text =
```

### Commands `:`
Wyrm has a number of commands that do various things from inserting prewritten text (like the complex doctypes of HTML/XHTML/XML) to defining the inheritance structure of a template. The current commands are the following:

#### `require`
`require` allows a template to assert that particular variables must be included in its rendering context. If any of the specified variables are not included, the template will fail to render. This is useful because when a variable is not defined in the context, it is always taken to be some particular value, by default `''`. It takes as arguments a comma-separated list of unquoted variable names. Example:
```
:require first, second, third
```

#### `include`
`include` renders another template as part of this one. This is the workhorse of the inheritance system, and is used both for including sub-templates and for extending base templates. It is used with `block` (see below) to override portions of the included templates. It takes as its first argument one of the following:
- a string giving the path to a template, when combined with one of the search directories defined in the engine config, and the file extension `.wyrm`;
- an expression that evaluates in the current context to a string as specified above;
- an expression that evaluates to a `Template` object

It can also take a list of keyword arguments, of the form `{name}={value}`, introduced by the `with` or `with only` keyword. In the case of `with`, these keyword arguments are added to the current context and used to render the included template, and in the case of `with only`, the keyword arguments are the only context variables used to render the included template.
Example:
```
:include 'base.html' with header_colour='blue', title='Community Forum'
```

#### `block`
`block` is used to define and override sections of templates in conjunction with `include`, as part of the inheritance system. This should not be confused with indentation-defined code blocks. As the direct child of an `include` command, it overrides blocks in the included template (as well as any templates *it* includes, and so on) with its own contents, while anywhere else it defines an overridable section of the document, whose contents are the default to be used in case the block does not get overridden. It takes as an argument a single unquoted string, serving as the block's identifier. Example:
```
:block mainContent
```

#### `html`
`html` is used to generate a doctype along with an `<html>` tag. The arguments to `html` are a little complex, as they come in two sets: arguments to select the correct doctype, and attributes to the `<html>` tag. The doctype selectors come first, and can be one of the following:
- no argument given. This defaults to the default doctype given in the config, currently HTML 5.
- `5`: HTML 5
    - `<!doctype html>`
- `4` or `4 strict`: HTML 4.01 Strict
    - `<!doctype html PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">`
- `4 transitional`: HTML 4.01 Transitional
    - `<!doctype html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">`
- `4 frameset`: HTML 4.01 Frameset
    - `<!doctype html PUBLIC "-//W3C//DTD HTML 4.01 Frameset//EN" "http://www.w3.org/TR/html4/frameset.dtd">`
- `1` or `1 strict`: XHTML 1.0 Strict
    - `<!doctype html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">`
- `1 transitional`: XHTML 1.0 Transitional
    - `<!doctype html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">`
- `1 frameset`: XHTML 1.0 Frameset
    - `<!doctype html PUBLIC "-//W3C//DTD XHTML 1.0 Frameset//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-frameset.dtd">`
- `1.1` XHTML 1.1
    - `<!doctype html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">`

Attributes are put after the doctype selectors, and follow the format used by other HTML tags, for which see there.

#### `css`, `js`, `md`
`css`, `js`, and `md` are used to include CSS, Javascript, and markdown respectively. Each command can either have a single argument, evaluating to a string giving the filename of a file to include (where the appropriate file extension is added automatically), or they can have a block with appropriately formatted plaintext. In the case of `css` and `js`, the commands will render to the appropriate HTML tags (`<link>` or `<style>` for `css`, and `<script>` for `js`), while `md` renders directly to HTML. Examples:
```
:js 'link/to/script'
:md
    # Embedded Markdown!
```

### Control code `-`
There are two systems of flow control in Wyrm, `if` and `for`. `if` allows blocks to be displayed conditionally, while `for` allows blocks to be displayed multiple times, once for each item in an iterable. There is also `with`, which allows binding expressions to local names.

#### `if`, `elif`, `else`
`if`, `elif`, and `else` are used together exactly as in Python to construct complex conditional statements. `if` and `elif` take a single expression as an argument, which will be cast to a boolean if it doesn't evaluate as such. The normal Python treatment of objects is used for this, so empty strings, lists, tuples, and dictionaries are all considered `False`, for example.

The initial `if` clause may be followed by zero or more `elif` clauses, which cannot occur otherwise, and finally by an optional `else` clause that takes no arguments.
```
- if expr1
    Displayed if expr1 is truthy
- elif expr2
    Displayed if expr1 is falsey and expr2 is truthy
- else
    Displayed if neither expr1 or expr2 are truthy
```

#### `for`, `empty`, `else`
`for`, `empty`, and `else` are used together in a way that's similar to Python's for loops, but differs in the behaviour of the `else` clause. The initial `for` is followed by a comma-separated list of one or more variable names, the `in` keyword, and then an expression that must evaluate to an iterable object. As in Python, for each iteration of the loop the next item of the iterable will be taken and assigned to the variable name(s), with sequence unpacking if necessary. If sequence unpacking occurs, the length of the sequence must exactly match the number of variable names provided. Unlike Python, these variables are only available inside the loop.

The for loop sets a number of additional variables inside the loop, giving information about the current state:
- `loop.counter`: the current iteration of the loop (0-based)
- `loop.counter1`: same as `loop.counter`, but 1-based
- `loop.revcounter`: the number of iterations from the end of the loop (0-based)
- `loop.revcounter1`: same as `loop.revcounter`, but 1-based
- `loop.first`: `True` if this is the first iteration
- `loop.last`: `True` if this is the last iteration
- `loop.parent`: if this loop is nested inside another for loop, this denotes the `loop` variable of that outer loop. If there is no outer loop, this is `None`.

After the `for` loop completes, the `else` clause, if provided, will be displayed after the results of the looping, but only if the iterable is not empty. If the iterable *is* empty, then the `empty` clause, if provided, will be displayed instead. Neither clause takes any arguments, and the order of the `else` and `empty` clauses doesn't matter.
```
- for name, age in authors
    % li: {name} is {age} years old.
- else
    % p: These are all the authors
- empty
    % p: There are no authors
```

#### `with`
`with` is used to bind the results of expressions to names, making them available within the nested block. A typical use is to "cache" the result of some complex operation, such as a call to the database. `with` takes a comma-separated list of keyword arguments, exactly like the keyword arguments introduced after the `with` keyword in an `include` command. Just like the `with` part of the `include` command, you can use `with only` to restrict the context inside the block to those defined in the `with` statement.
```
- with wordlist=lang.word_set.all()
```

### Output code `=`
While the values of expressions can be displayed via interpolating into plaintext, the preferred way to display just the value of a single expression, and nothing else, is to directly output it using the `=` line indicator. This evaluates whatever is to the right as an expression, and displays it. A typical use is to fill the contents of a tag:
```
% a href=link_target: = link_name
```

### Comments `/`
While many languages have both line and block comments, Wyrm only has line comments for hiding text from the rendered output. In order to hide blocks of text, each line must be commented out. Additionally, Wyrm doesn't have inline comments - each comment must be on its own line. Examples:
```
/ This line is not displayed
This line is displayed / And so is this
```

### HTML Comments `/!`
Wyrm can also display lines as HTML comments, passing them through to the rendered output. These comments can also contain interpolated expressions, exactly like plaintext:
```
/! This is an HTML comment, saying {foo}
```

### HTML Tags `%`
HTML tags are the mainstay of HTML (and XML) documents, and it is important to format them correctly, a task Wyrm takes care of for you. There are three parts of the tag: the name; class and id shortcuts; and the attributes. The tag name can be any valid identifier (see below), and while XML also allows `-` and `.` in tag names (though their use is discouraged), these are presently disallowed by Wyrm. In the case of `.`, this is due to collision with class shortcuts, as described below. `-` may in the future be allowed.

The tag name is followed by class and id shortcuts. These follow the CSS practice of specifying class names with a leading `.`, and id names with a leading `#`. These may optionally be preceded by a single space, but there must be no spaces after the `.` or `#`, or within the class or id names. Class and id names may contain any of the valid identifier characters, as well as `-`. If class or id shortcuts are given, and only if at least one is given, then the tag name may be omitted, and `div` will be assumed, due to the tag's high frequency in HTML.

The attributes are the last thing in the tag, and are given as a space-separated list of `{name}={value}` pairs, where the name is either a valid identifier, or (uniquely to HTML attributes) a string containing a sequence of identifiers joined by `-`, and the value is an expression that must evaluate to a string, an integer, or a boolean. A value evaluating to `False` will be treated as though the attribute was not included at all, while a value evaluating to `True` is equivalent to giving just the attribute name (thus mirroring HTML's binary attributes) as well as setting the attribute value to the same as the attribute name, but as a string (thus conforming to XHTML). If the `id` attribute is given here, it will be overridden by an id shortcut, while if the `class` attribute is given, it will be appended to by any class shortcuts.
```
% input #searchbox.roundable-border type="text" name="search" required
```

### Inlining blocks
It frequently occurs that a block consists of exactly one line (which may or may not have its own nested block), such as the text content of a tag. In these cases, it is possible to inline the block, writing it on the same line as its parent, by writing a `:`, optionally followed by a space, and then the inlined block. If a line containing an inlined block if followed by a nested block, it is considered to be a child of the last inlined block, making these two snippets fully equivalent:
```
- if permission: % p: % a href="www.google.com"
    A couple
    lines of
    text.
```
```
- if permission
    % p
        % a href="www.google.com"
            A couple
            lines of
            text.
```
While the use of `:` for inlining could potentially be confused with its use as a line indicator, in practice the two can always be told apart, as at the beginning of a line, `:` is always a line indicator, and in the middle of a line (outside of any brackets), a single `:` is always the inlining operator, and a double `:` (possibly separated by whitespace) is always the inlining operator followed by a line indicator.

