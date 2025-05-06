#!/usr/bin/env python3
import sys
import re
import textwrap
import dataclasses
import secrets

### These regexes are run after maple codegen, before everything is put in single quotes
###
### Use this to repair common mistakes and escape things if Mobius noms chars
fixup = [
    # This fixes accidental omission of output=string.
    #
    # It is very much imperfect, and using this function directly instead of the xform is generally unnecessary
    (r"latex +\(((?:(?!output\s*=)[^)])*)\)", r"latex(\1, output = string)"),
    # This escapes square brackets and single quotes, as these fail within single quotes in Mobius
    (r"([\[\]'/])", r"""'"\1"'""")
]

### Generates an SVG plot by writing it to disk, reading it back, and deleting the file
#
# Note that the flush here is 100% required and took me like an hour to work out why it wasn't working >:(
def maple_plot(x):
    return x.with_value(textwrap.dedent(f"""
    (proc()
        file := FileTools:-TemporaryFile("",".svg"):
        plottools:-exportplot(file, {x.value}):
        FileTools:-Text:-Close(file):
        data := "data:image/svg+xml;base64," || (StringTools:-Encode(FileTools:-Text:-ReadFile(file), encoding=base64)):
        FileTools:-Remove(file):
        data
    end proc)()""").strip())

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
    args = list(map(str.strip, x.split("|")))
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
            boilerplate = []
            # Extract the code and shrink the remaining portion
            code = code_match.group(1)
            remaining = code[code_match.end(1):]

            # Extract the exports and parse them
            matched_exports = re.findall(r'^\s*#!export\s*(.*)$', code, re.MULTILINE)
            exports = []
            for matched in matched_exports:
                exports += list(map(parse_export, filter(None, re.split(r',', matched))))

            # Directives
            norandom_directive = bool(re.search(r'^\s*#!evil_norandom$', code, re.MULTILINE))
            test_directive = bool(re.search(r'^\s*#!evil_test$', code, re.MULTILINE))
            reproduce_directive = re.search(r'^\s*#!evil_reproduce\s*(.*)$', code, re.MULTILINE)
            noassert_directive = re.search(r'^\s*#!evil_noassert\s*(.*)$', code, re.MULTILINE)

            # Add exports to maple code
            export_maple = ", ".join(i.value for i in exports)
            code += "\n# Generated code follows:\nprint(" + export_maple + ");\n"

            # Handle noassert
            if noassert_directive:
                pass
            # Check if in debug mode
            elif re.search(r'^\s*#!evil_debug$', code, re.MULTILINE) or reproduce_directive:
                code = f'kernelopts(assertlevel=1);\n{code}'
            # Check if in test mode
            elif test_directive:
                prefix = f'august_internal_{secrets.token_hex(8)}_'
                state_var = f'{prefix}state'
                iter_var = f'{prefix}iter'
                code = fr"""local ASSERT := proc(x, y := "assertion failed") if not x then error(y) fi end proc:
for {iter_var} from 1 do
    try
        {state_var} := RandomTools:-GetState();
{textwrap.indent(code, "        ")}
        next:
    catch:
        error(sprintf("<br>Error: %s<br>Loop: %d<br>Reproduce with:<pre>#!evil_reproduce %s</pre>", lastexception[2], {iter_var}, convert({state_var}, string)));
        stop;
    end try:
end;"""
            else:
                code = fr"""local ASSERT := proc(x, y := "assertion failed") if not x then error(y) fi end proc:
do
    try
{textwrap.indent(code, "        ")}
        break:
    catch: next
    end try:
end:"""

            if reproduce_directive:
                code = f'# DO NOT DEPLOY THIS: forcing seed\nRandomTools:-SetState(state={reproduce_directive.group(1)}):\n{code}'
                
            # Check to see if we need the rng boilerplate
            elif not norandom_directive:
                # Generate a unique naming prefix
                rng_var_prefix = f'august_internal_{secrets.token_hex(8)}_'
                # Anything >= 1e9 will be converted into scientific notation
                # Also, for some reason known only unto god, `rint` seems to be bounded by the 32 bit signed integer limit
                boilerplate.append(textwrap.dedent(fr"""
                    # Generating seed for upcoming maple block
                    ${rng_var_prefix}0 = rint(1E9);
                    ${rng_var_prefix}1 = rint(1E9);
                """).strip())
                code = f'# Seeding from Mobius-supplied result\nrandomize(${rng_var_prefix}0 * 1000000000 + ${rng_var_prefix}1):\n{code}'.strip()
            # Indent
            code = textwrap.indent(code, "    ")
            # Fixups
            for (match, subs) in fixup:
                code = re.sub(match, subs, code)

            # Put frame around
            code = f"""$maple_result = maple('\n{code}\n');\n"""
            # Apply boilerplate
            if boilerplate:
                code = f"{'\n'.join(boilerplate)}\n{code}"
            # Add exports to mobius code
            code += '\n'.join(f"${i.name} = switch({idx}, $maple_result);" for idx, i in enumerate(exports))
            print(code)
    return 0
sys.exit(main())
