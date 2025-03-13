# August
_FFI for Mobius_

# Usage
Just call `august.py` with a path to your script file, and it will print the generated Mobius code

# Script documentation
## Mobius code
Mobius code can be stored within `(*!mobius *)` blocks. Be aware that each one of these splits the maple code, so if you have one anywhere else but the very beginning or very end of your script, you will end up with multiple `maple` calls. A situtation that requires this should never happen, so please raise an issue if you come across one!
## Exports
You can export the variables `foo` and `bar` from Maple to Mobius like so:
```
#!export foo, bar
```
This will create Mobius variables `$foo` and `$bar` respectively. If you want to use the transforms (described later) `quux` then `wibble(3)` with `baz` as well, you can write:
```
#!export foo, bar, baz|quux|wibble(3)
```
## Transforms
### `latex`
This converts the value to latex
### `plot`
This emulates the behaviour of `plotmaple`, but allows the plot to be bundled with other variables, allowing you to only use one `maple` block. This will export a very long string, which you can use as a source in an image tag.

For instance, consider the following code:
```
foo := plot(x^2);
#!export foo|plot
```
This will create a `$foo` Mobius variable. In a question (or answer), you can add an image with a URL of `$foo` and alternative text describing the plot. For those who want to use the HTML editor, you can use `<img src="$foo" />` to get the same result. Be aware that not putting in alternative text will result in the image not showing up in the editor!
### `suffix`
`foo|suffix(bar)` will result in the corresponding mobius variable being called `foo_bar`
### `dp`
`foo|dp(3)` will give a float rounded to 3 decimal places.
## Fixups
August also fixes a couple of common mistakes, such as forgetting to put `output=string` into Maple's `latex` function. It also escapes characters, allowing you to use quotes and brackets without drawing Mobius' ire.
