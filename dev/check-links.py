#!/usr/bin/env python3
"""Checks every link in the plugins' Markdown files, and every guide named across domains:

- a relative link [text](path#anchor) points to a file that exists, and to a heading that exists in it; inside a plugin, to
  a file of the same plugin, since each plugin is installed on its own;
- a `domain:skill` name, such as `modeling:characters`, names a skill of a domain of this marketplace.

Usage: python3 dev/check-links.py     prints each broken link and exits 1, or prints nothing
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINK = re.compile(r"\]\(([^)\s]+)\)")
NAME = re.compile(r"`([a-z][a-z0-9-]*):([a-z][a-z0-9-]*)`")
FENCE = re.compile(r"^\s*```")


def slug(heading):
    text = heading.strip().lower().replace("`", "")
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def anchors(path, cache={}):
    if path not in cache:
        found = set()
        fenced = False
        with open(path, encoding="utf-8") as f:
            for line in f:
                if FENCE.match(line):
                    fenced = not fenced
                if not fenced and line.startswith("#"):
                    found.add(slug(line.lstrip("#")))
        cache[path] = found
    return cache[path]


def main():
    market = json.load(open(os.path.join(ROOT, ".claude-plugin", "marketplace.json")))
    domains = {}
    for entry in market["plugins"]:
        folder = os.path.normpath(os.path.join(ROOT, entry["source"]))
        domains[entry["name"]] = set(os.listdir(os.path.join(folder, "skills")))

    problems = []
    files = [os.path.join(ROOT, "README.md"), os.path.join(ROOT, "CLAUDE.md")]
    for dirpath, _, names in os.walk(os.path.join(ROOT, "plugins")):
        if os.sep + "templates" in dirpath:
            continue  # a template's links are the future project's, not this repository's
        files += [os.path.join(dirpath, n) for n in names if n.endswith(".md")]

    for path in files:
        rel = os.path.relpath(path, ROOT)
        fenced = False
        with open(path, encoding="utf-8") as f:
            for number, line in enumerate(f, 1):
                if FENCE.match(line):
                    fenced = not fenced
                    continue
                if fenced:
                    continue
                for target in LINK.findall(re.sub(r"`[^`]*`", "", line)):  # inline code shows links, it holds none
                    if re.match(r"^[a-z]+:", target) or target.startswith("<"):
                        continue
                    file_part, _, anchor = target.partition("#")
                    goal = path if not file_part else os.path.normpath(os.path.join(os.path.dirname(path), file_part))
                    if not os.path.exists(goal):
                        problems.append(f"{rel}:{number}: no file {target}")
                    elif rel.startswith("plugins" + os.sep):
                        plugin = os.path.join(ROOT, *rel.split(os.sep)[:2])
                        if os.path.commonpath([plugin, goal]) != plugin:
                            problems.append(f"{rel}:{number}: {target} leaves its plugin, which is installed on its own")
                    elif anchor and goal.endswith(".md") and anchor not in anchors(goal):
                        problems.append(f"{rel}:{number}: no heading #{anchor} in {os.path.relpath(goal, ROOT)}")
                for domain, skill in NAME.findall(line):
                    if domain in domains and skill not in domains[domain]:
                        problems.append(f"{rel}:{number}: no skill {skill} in domain {domain}")

    if problems:
        print("\n".join(problems))
        sys.exit(1)


if __name__ == "__main__":
    main()
