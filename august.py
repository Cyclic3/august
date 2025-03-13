import sys
import re
import textwrap
import dataclasses

fixup = [
    (r"latex\((.*(?!output\s*=))\)", r"latex(\1, output = string)"),
    (r"([\[\]'])", r"""'"\1"'""")
]

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
    name: str
    value: str
    def with_name(self, new_name: str) -> 'Export':
        return Export(new_name, self.value)
    def with_value(self, new_value: str) -> 'Export':
        return Export(self.name, new_value)

xforms = {
	"latex": lambda x: x.with_value(f"latex({x.value}, output = string)"),
	"plot": maple_plot,
    "suffix": lambda x, y: x.with_name(f'{x.name}_{y}'),
    "dp": lambda x, y: x.with_value(fr"""sprintf("%.0{y}f", {x.value})""")
}

def do_xform(x):
    x = x.strip()
    args = x.split("|")
    if len(args) == 1:
        return Export(x, f"convert({x}, string)")
    var = Export(args[0], args[0])
    requested_xforms = args[1:]
    for i in requested_xforms:
        split = re.match(r"([^(]*)(?:\((.*)\))?", i)
        if split.lastindex == 1:
            var = xforms[split.group(1)](var)
        else:
            var = xforms[split.group(1)](var, split.group(2))
    return var

def main():
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
            code = code_match.group(1)
            remaining = code[code_match.end(1):]
            matched_exports = re.findall(r'#!export\s*(.*)', code)
            exports = []
            for matched in matched_exports:
                exports += list(map(do_xform, filter(None, re.split(r',|\s', matched))))
            # Add exports to maple code
            export_maple = ", ".join(i.value for i in exports)
            code += "\n# Generated code follows:\n" + export_maple + ";\n"
            # Indent
            code = '\n'.join("    " + i for i in code.splitlines())
            # Fixups
            for (match, subs) in fixup:
                code = re.sub(match, subs, remaining)
            # Put frame around
            code = f"""$maple_result = maple('\n{code}\n');\n"""
            # Add exports to mobius code
            code += '\n'.join(f"${i.name} = switch({idx}, $maple_result);" for idx, i in enumerate(exports))
            print(code)
main()
