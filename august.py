#!/usr/bin/env python3
import sys
import re
import textwrap
import dataclasses

### These regexes are run after maple codegen, before everything is put in single quotes
###
### Use this to repair common mistakes and escape things if Mobius noms chars
fixup = [
    # This fixes accidental omission of output=string.
    #
    # It is very much imperfect, and using this function directly instead of the xform is generally unnecessary
    (r"latex[ ]+\(((?:(?!output\s*=)[^)])*)\)", r"latex(\1, output = string)"),
    # This escapes square brackets and single quotes, as these fail within single quotes in Mobius
    (r"([\[\]'])", r"""'"\1"'""")
]

### Generates an SVG plot by writing it to disk, reading it back, and deleting the file
#
# Note that the flush here is 100% required and took me like an hour to work out why it wasn't working >:(
def maple_plot(x):
    return x.with_value(f"""(proc()
      file := FileTools:-TemporaryFile("",".svg"):
      plottools:-exportplot(file, {x}):
      FileTools:-Text:-Close(file):
      data := "data:image/svg+xml;base64," || (StringTools:-Encode(FileTools:-Text:-ReadFile(file), encoding=base64)):
      FileTools:-Remove(file):
      data
    end proc)()""")

@dataclasses.dataclass
class Export:
    """A variable that will be exported"""
    name: str
    """The variable name that will be exported to mobius (after a $ is appended)"""
    value: str
    """The value used to generate it in maple"""
    def with_name(self, new_name: str) -> 'Export':
        """Returns a new object with the same value and the supplied name"""
        return Export(new_name, self.value)
    def with_value(self, new_value: str) -> 'Export':
        """Returns a new object with the same name and the supplied value"""
        return Export(self.name, new_value)

### The transforms that will be applied if requested to an export
###
### Each needs to be of the form Export -> Export for xforms without an argument,
### or (Export, str) -> Export for exforms with more than one argument.
###
### Note that the argument is not parsed for you!
xforms = {
	"latex": lambda x: x.with_value(f"latex({x.value}, output = string)"),
	"plot": maple_plot,
    "suffix": lambda x, y: x.with_name(f'{x.name}_{y}'),
    "dp": lambda x, y: x.with_value(fr"""sprintf("%.0{y}f", {x.value})"""),
    "string": lambda x: x.with_value(f"convert({x.value}, string)")
}

def parse_export(x):
    """Evaluates an export string into a name and value, applying any requested transforms"""
    # Split out transforms
    x = x.strip()
    args = x.split("|")
    # The default export is just name and name
    var = Export(args[0], args[0])
    # Default to just the string transform
    if len(args) == 1:
        return xforms["string"](var)
    # Otherwise just apply each transform
    requested_xforms = args[1:]
    for i in requested_xforms:
        # Check if there are arguments
        split = re.match(r"([^(]*)(?:\((.*)\))?", i)
        if split.lastindex == 1:
            var = xforms[split.group(1)](var)
        else:
            # We don't parse the argument, just pass it straight through
            var = xforms[split.group(1)](var, split.group(2))
    return var

def main():
    if len(sys.argv) != 2:
        print(F"Usage: {sys.argv[0]} <SCRIPT_PATH>", file=sys.stderr)
        return 1

    with open(sys.argv[1], encoding="utf-8") as file:
        remaining = file.read()
    
    # Match comments
    while len(remaining := remaining.strip()) > 0:
        mobius_match = re.match(r"\(\*!mobius[^\n]*\n?((?:[^*]|\*[^)])*?)[\s]*\*\)", remaining, re.MULTILINE)
        if mobius_match:
            print(textwrap.dedent(mobius_match.group(1)))
            remaining = remaining[mobius_match.end(0):]
            continue
        code_match = re.match(r"((?:[^(]|\([^*]|\(\*[^!]|)*)", remaining, re.MULTILINE)
        if code_match:
            # Extract the code and shrink the remaining portion
            code = code_match.group(1)
            remaining = code[code_match.end(1):]
            # Extract the exports and parse them
            matched_exports = re.findall(r'#!export\s*(.*)', code)
            exports = []
            for matched in matched_exports:
                exports += list(map(parse_export, filter(None, re.split(r',|\s', matched))))
            # Add exports to maple code
            export_maple = ", ".join(i.value for i in exports)
            code += "\n# Generated code follows:\n" + export_maple + ";\n"
            # Indent
            code = textwrap.indent(code, "    ")
            # Fixups
            for (match, subs) in fixup:
                code = re.sub(match, subs, remaining)
            # Put frame around
            code = f"""$maple_result = maple('\n{code}\n');\n"""
            # Add exports to mobius code
            code += '\n'.join(f"${i.name} = switch({idx}, $maple_result);" for idx, i in enumerate(exports))
            print(code)
    return 0
sys.exit(main())
