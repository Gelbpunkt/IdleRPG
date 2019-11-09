with open("schema.sql", "r") as f:
    stuff = f.read().splitlines()

t = ""
c = []
in_t = False
for line in stuff:
    if line.startswith("CREATE TABLE"):
        t = line.split()[2].split(".")[1]
        in_t = True
        print(t)
    elif in_t:
        if line == ");":
            print(c)
            t = ""
            in_t = False
            c = []
        else:
            c.append(line.split()[0].strip('"'))
