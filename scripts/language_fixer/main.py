#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re


def replace(file: str, pattern: str, new: str):
    pattern = pattern.replace("�", "\\n")
    with open(file, "r+", encoding="utf-8", errors="ignore") as f:
        cont = f.read()
        print(pattern in cont)
        cont = cont.replace(pattern, new)
        f.seek(0)
        f.write(cont)
        f.truncate()


def search(pattern: str):
    for root, folders, files in os.walk("."):
        for file in files:
            if not file.endswith(".py"):
                continue
            with open(os.path.join(root, file), "r", errors="ignore") as f:
                text = f.read()

                pattern = pattern.replace("\\n", "�")
                match = re.search(pattern, text.replace("\\n", "�"), flags=re.MULTILINE)
                if match:
                    return os.path.join(root, file), match[0]
    return None


if __name__ == "__main__":
    print("IdleRPG Language Fixer")
    print("----------------------")
    print()
    print("This tool will ask you")
    print("for a bad text you saw")
    print("in Poedit's English.")
    print("Copy it here.")
    print()
    bad_line = ""
    count = 0
    while count == 0 or bad_line.endswith("\\n"):
        bad_line += input("> ")
        count += 1
    print("Thanks, I'm going to")
    print("search for it!")
    print()

    result = search(bad_line)
    if result is None:
        print("Not found.")
    else:
        result, bad_line = result
        print(f"First match in {result}!")
        print("Please enter the correct")
        print("text you want it to be")
        new_line = ""
        count = 0
        while count == 0 or new_line.endswith("\\n"):
            new_line += input("> ")
            count += 1
        replace(result, bad_line, new_line)
        print("Replaced.")
