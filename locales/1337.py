import os
import sys

try:
    with open(sys.argv[1], "r") as f:
        cont = f.read().splitlines()
except (IndexError, FileNotFoundError):
    print("Please provide a .po file.")
    exit(0)

empty = input("Is the msgstr empty? (y/n) ")
out = []
is_in_msgstr = False
is_in_b = False
is_in_c = False
buf = ""
mapping = {"a": "4", "e": "3", "g": "6", "i": "1", "o": "0", "s": "5", "t": "7"}
for no, line in enumerate(cont):
    if not line or line.startswith("#") or no < 18:  # ignore
        out.append(line)
    else:
        if line.startswith("msgid"):
            prefix = "msgid"
            is_in_msgstr = False
            line = line[6:]
        elif line.startswith("msgstr"):
            prefix = "msgstr"
            is_in_msgstr = True
            line = line[7:]
        else:
            prefix = ""
        if empty == "y":
            if is_in_msgstr:
                line = ""
                for j, i in enumerate(buf):
                    if i == "{":
                        is_in_b = True
                    elif i == "}":
                        is_in_b = False
                    if i == "`" and buf[j + 1 : j + 9] == "{prefix}":
                        is_in_c = True
                    elif i == "`" and is_in_c:
                        is_in_c = False
                    if (not is_in_b) and (not is_in_c):
                        line = f"{line}{mapping.get(i.lower(), i)}"
                    else:
                        line = f"{line}{i}"
                buf = ""
            else:
                buf = f"{buf}{line}\n"
        else:
            if is_in_msgstr:
                new_line = ""
                for j, i in enumerate(line):
                    if i == "{":
                        is_in_b = True
                    elif i == "}":
                        is_in_b = False
                    if i == "`" and line[j + 1 : j + 9] == "{prefix}":
                        is_in_c = True
                    elif i == "`" and is_in_c:
                        is_in_c = False
                    if (
                        (not is_in_b)
                        and (not is_in_c)
                        and (not (i == "t" and line[j - 1] == "\\"))
                    ):
                        new_line = f"{new_line}{mapping.get(i.lower(), i)}"
                    else:
                        new_line = f"{new_line}{i}"
                line = new_line
        out.append(f"{prefix} {line}")


out = "\n".join(out).replace("\n\n\n", "\n\n")

name = input("Locale code? ")
if not os.path.isdir(name):
    os.mkdir(name)
    os.mkdir(name + os.sep + "LC_MESSAGES")
else:
    os.remove(os.path.join(name, "LC_MESSAGES", "idlerpg.po"))
with open(os.path.join(name, "LC_MESSAGES", "idlerpg.po"), "w") as f:
    f.write(out)

print("Done.")
