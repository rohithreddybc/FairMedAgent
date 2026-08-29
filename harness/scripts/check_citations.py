"""Integrity check: every \\cite{} key in the paper resolves to a verified references.bib entry."""
import re
import os

P = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "paper"))
tex = open(os.path.join(P, "main.tex"), encoding="utf-8").read()
bib = open(os.path.join(P, "references.bib"), encoding="utf-8").read()

CITE = "\\" + "cite{"   # avoid literal backslash-c escape headaches
used = set()
i = 0
while True:
    i = tex.find(CITE, i)
    if i < 0:
        break
    j = tex.find("}", i)
    for k in tex[i + len(CITE):j].split(","):
        if k.strip():
            used.add(k.strip())
    i = j

bibkeys = set(re.findall(r"@\w+\{([^,]+),", bib))
missing = used - bibkeys
print("unique cite keys used:", len(used))
print("bib entries:", len(bibkeys))
print("USED BUT MISSING:", sorted(missing) if missing else "NONE - all citations resolve")
print("verified-but-unused:", sorted(bibkeys - used))
finals = tex.count("\\" + "final{")
print("remaining \\final{} placeholders:", finals)

# Abstract word count (IEEE JBHI limit: <=250 words)
a0 = tex.find("\\begin{abstract}")
a1 = tex.find("\\end{abstract}")
if a0 >= 0 and a1 > a0:
    ab = tex[a0 + len("\\begin{abstract}"):a1]
    ab = re.sub(r"\\final\{[^}]*\}", "", ab)          # drop gated placeholder text
    ab = re.sub(r"\\[a-zA-Z]+\*?", " ", ab)            # drop LaTeX commands
    ab = re.sub(r"[{}~\\$]", " ", ab)                  # drop stray tokens
    words = [w for w in ab.split() if any(c.isalnum() for c in w)]
    print(f"abstract word count: {len(words)}  (IEEE limit 250) ->", "OK" if len(words) <= 250 else "OVER LIMIT")
