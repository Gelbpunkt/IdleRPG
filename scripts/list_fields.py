with open("schema.sql", "r") as f:
    stuff = f.read().splitlines()

t = ""
c = []
in_t = False
for l in stuff:
    if l.startswith("CREATE TABLE"):
        t = l.split()[2].split(".")[1]
        in_t = True
        print(t)
    elif in_t:
        if l == ");":
            print(c)
            t = ""
            in_t = False
            c = []
        else:
            c.append(l.split()[0].strip('"'))
