#!/usr/bin/env python3
"""Write `.zenodo.json` from the paper itself, so the deposit cannot say anything the paper does not.

The abstract is the paper's abstract with its macros resolved by `export_paper_tables.numbers()`;
the references are the paper's bibliography; the related identifiers are the arXiv ids in it.
`tests/test_paper.py` requires the committed file to equal a fresh build (D046).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import export_paper_tables as ex  # noqa: E402

TITLE = ("Affirming Unattested Expertise at Ceiling Confidence: "
         "Auditing a Search-Augmented Answer Endpoint and Five Harness Failure Modes")
ACCENTS = {r"{\'e}": "é", r"{\"a}": "ä", r"\'e": "é", r"\"a": "ä"}
NOTES = ("Work begun 2 September 2026 (first repository commit fad6dc8); paper first compiled "
         "and deposited 23 November 2026 (paper-v1.0, Zenodo record 24454863). This version, "
         "paper-v2.0, is of 23 November 2026.")


def tex_to_text(s: str, m: dict[str, str]) -> str:
    s = re.sub(r"\\(ti[A-Z]\w*)\{\}", lambda g: m[g[1]].replace("{,}", ","), s)
    s = re.sub(r"\\texttt\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\emph\{([^}]*)\}", r"\1", s)
    s = s.replace(r"\ensuremath{-}", "-").replace("$-$", "-")
    s = s.replace(r"\%", "%").replace("$", "").replace("~", " ").replace(r"\,", " ")
    s = s.replace("---", " — ").replace("--", "-").replace(r"\ge", ">=").replace(r"\noindent", "")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def abstract(m: dict[str, str]) -> str:
    tex = (ROOT / "paper" / "titer.tex").read_text()
    body = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", tex, re.S).group(1)
    return tex_to_text(body, m)


def unbrace(s: str) -> str:
    for a, b in ACCENTS.items():
        s = s.replace(a, b)
    return s.replace("{", "").replace("}", "").replace("--", "-")


def parse_bib() -> list[dict[str, str]]:
    out = []
    for entry in re.split(r"\n(?=@)", (ROOT / "paper" / "refs.bib").read_text()):
        if not entry.startswith("@"):
            continue
        fields = {}
        for k, v in re.findall(r"^\s*(\w+)\s*=\s*\{(.*?)\},?\s*$", entry, re.M | re.S):
            fields[k] = re.sub(r"\s+", " ", v)
        out.append(fields)
    return out


def fmt_author(a: str) -> str:
    a = unbrace(a.strip())
    if a == "others":
        return "et al."
    last, _, first = a.partition(",")
    initials = " ".join(p[0] + "." for p in re.split(r"[ ]+", first.strip()) if p and p[0].isalpha())
    return f"{last.strip()}, {initials}".strip().rstrip(",")


def reference(f: dict[str, str]) -> str:
    authors = [fmt_author(a) for a in f["author"].split(" and ")]
    if authors[-1] == "et al.":
        who = ", ".join(authors[:-1]) + ", et al."
    elif len(authors) == 1:
        who = authors[0]
    else:
        who = ", ".join(authors[:-1]) + ", & " + authors[-1]
    title = unbrace(f["title"])
    venue = ""
    if "journal" in f:
        venue = unbrace(f["journal"])
        if "volume" in f:
            venue += f", {f['volume']}" + (f"({f['number']})" if "number" in f else "")
        if "pages" in f:
            venue += f", {unbrace(f['pages'])}"
    elif "booktitle" in f:
        venue = unbrace(f["booktitle"])
        if "pages" in f:
            venue += f", pp. {unbrace(f['pages'])}"
    if "note" in f:
        venue = (venue + ". " if venue else "") + f["note"]
    if "doi" in f:
        venue += f". https://doi.org/{f['doi']}"
    return f"{who} ({f['year']}). {title}. {venue}.".replace("..", ".")


def arxiv_ids(bib: list[dict[str, str]]) -> list[str]:
    ids = []
    for f in bib:
        m = re.search(r"arXiv:(\d{4}\.\d{4,5})", " ".join(f.values()))
        if m:
            ids.append(m[1])
    return ids


def build() -> dict:
    m = ex.numbers()
    bib = parse_bib()
    desc = abstract(m) + " Not peer reviewed. Code and protocol: https://github.com/caiotheodoro/titer"
    related = [
        {"relation": "isSupplementedBy", "identifier": "https://github.com/caiotheodoro/titer",
         "resource_type": "software", "scheme": "url"},
        {"relation": "isSupplementedBy", "identifier": "https://huggingface.co/datasets/caiotheodoro/titer-edgar-officers",
         "resource_type": "dataset", "scheme": "url"},
        {"relation": "isSupplementedBy", "identifier": "https://huggingface.co/datasets/caiotheodoro/titer-expertise-claims",
         "resource_type": "dataset", "scheme": "url"},
    ] + [{"relation": "cites", "identifier": f"arXiv:{i}", "resource_type": "publication-preprint", "scheme": "arxiv"}
         for i in arxiv_ids(bib)]
    return {
        "title": TITLE,
        "upload_type": "publication",
        "publication_type": "preprint",
        "creators": [{"name": "Theodoro, Caio", "orcid": "0009-0005-7343-981X"}],
        "publication_date": "2026-09-02",
        "license": "cc-by-4.0",
        "description": desc,
        "notes": NOTES,
        "keywords": ["expertise verification", "expertise retrieval", "calibration",
                     "benchmark auditing", "measurement error", "pre-registration"],
        "language": "eng",
        "related_identifiers": related,
        "references": [reference(f) for f in bib],
        "version": "paper-v2.0",
    }


def main() -> int:
    (ROOT / ".zenodo.json").write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n")
    print("wrote .zenodo.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
