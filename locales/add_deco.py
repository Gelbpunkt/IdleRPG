# adds the @locale_doc deco to all commands and groups in POTFILES
with open("POTFILES.in", "r") as f:
    files = f.read().splitlines()

for file in files:
    with open(f"../{file}", "r+") as f:
        stuff = f.read().splitlines()
        stuff2 = stuff
        done = 0
        for idx, line in enumerate(stuff):
            if "@" in line and (".group" in line or ".command" in line):
                stuff2.insert(idx + 1, "    @locale_doc")
                done += 1 
        f.seek(0)
        f.write("\n".join(stuff2))
        f.truncate()
