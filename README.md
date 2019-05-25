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
        | % You can make it explicit instead. %
        Text also supports interpolating {variables} with curly brackets.

        - if output
            Simple flow control
        - for feature in feature_list
            = feature
            Output variables directly
        - empty
            Easy looping as well
```
# Syntax

## Blocks
Wyrm uses indentation to define blocks, though the indentation level can be arbitrary, and can differ from block to block. All that matters is that all lines that are supposed to be in the same block have the same indentation.

## Line indicators
Wyrm uses the punctuation characters `: - = / %` to explicitly mark the various types of line. All line indicators may be optionally followed by a single space, to enhance readability.

## Commands `:`
Wyrm has a number of commands that do various things from inserting prewritten text (like the complex doctypes of HTML/XHTML/XML) to defining the inheritance structure of a template. The current commands are the following:

### `require`
`require` allows a template to assert that particular variables must be included in its rendering context. If any of the specified variables are not included, the template will fail to render. It takes as arguments a comma-separated list of unquoted variable names. Example:
```
:require first, second, third
```

### `include`
`include` renders another template as part of this one. This is the workhorse of the inheritance system, and is used both for including sub-templates and for extending base templates. It is used with `block` (see below) to override portions of the included templates. It takes as its first argument one of the following:
- a string giving the path to a template, when combined with one of the search directories defined in the engine config, and the file extension `.wyrm`;
- an expression that evaluates in the current context to a string as specified above;
- an expression that evaluates to a `Template` object
It can also take a list of keyword arguments, of the form `{name}={value}`, introduced by the `with` or `with only` keyword. In the case of `with`, these keyword arguments are added to the current context and used to render the included template, and in the case of `with only`, the keyword arguments are the only context variables used to render the included template.
Example:
```
:include 'base.html' with header_colour='blue', title='Community Forum'
```

### `block`
`block` is used to define and override sections of templates in conjunction with `include`, as part of the inheritance system. This should not be confused with indentation-defined code blocks. As the direct child of an `include` command, it overrides blocks in the included template (as well as any templates *it* includes, and so on) with its own contents, while anywhere else it defines an overridable section of the document, whose contents are the default to be used in case the block does not get overridden. It takes as an argument a single unquoted string, serving as the block's identifier. Example:
```
:block mainContent
```

### `css`, `js`, `md`
`css`, `js`, and `md` are used to include CSS, Javascript, and markdown respectively. Each command can either have a single argument, evaluating to a string giving the filename of a file to include (where the appropriate file extension is added automatically), or they can have a block with appropriately formatted plaintext. In the case of `css` and `js`, the commands will render to the appropriate HTML tags (`<link>` or `<style>` for `css`, and `<script>` for `js`), while `md` renders directly to HTML. Examples:
```
:js 'link/to/script'
:md
    # Embedded Markdown!
```

