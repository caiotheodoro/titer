"""The paper's numbers are tied to the committed results (D046).

Four defects this guards, each one that happened somewhere in this project or a sibling:

* a number typed into prose that no artifact backs;
* a generated table that drifted from its generator;
* doubled backslashes, which compile cleanly and silently eat text (the build stays green);
* a citation or reference that does not resolve, which prints as "?" in the PDF.

The README's four-decimal figures are held to the same standard against `results/`.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import export_paper_tables as ex  # noqa: E402
import export_zenodo as ez  # noqa: E402

TEX = ROOT / "paper" / "titer.tex"
BIB = ROOT / "paper" / "refs.bib"
GEN = ROOT / "paper" / "generated"


def _prose() -> str:
    """The paper source without comment lines."""
    return "\n".join(l for l in TEX.read_text().splitlines() if not l.lstrip().startswith("%"))


def test_generated_files_equal_a_fresh_build() -> None:
    for name, text in ex.build().items():
        assert (GEN / name).read_text() == text, f"{name} drifted; run scripts/export_paper_tables.py"


def test_no_stray_generated_files() -> None:
    assert {p.name for p in GEN.iterdir()} == set(ex.build())


def test_every_macro_used_is_defined_and_every_input_exists() -> None:
    prose = _prose()
    defined = set(re.findall(r"\\newcommand\{\\(\w+)\}", (GEN / "numbers.tex").read_text()))
    used = set(re.findall(r"\\(ti[A-Z]\w*)", prose))
    assert not used - defined, f"undefined macros: {sorted(used - defined)}"
    for rel in re.findall(r"\\input\{([^}]+)\}", prose):
        assert (TEX.parent / f"{rel}.tex").is_file(), rel


def test_no_doubled_backslashes_in_prose() -> None:
    """vernier lost an abstract and a result to `\\%` and `\\cmd`; the PDF built and CI stayed green.
    A row-ending `\\\\` is legitimate, so only a doubled backslash glued to text is refused."""
    bad = [l for l in _prose().splitlines() if re.search(r"\\\\(?!small)(?=[%A-Za-z{$])", l)]
    assert not bad, bad[:3]


def test_every_decimal_literal_in_prose_is_a_generated_value() -> None:
    """A measured number cannot be typed into the paper. Decimals must be produced by the exporter,
    or be on this short list of constants that are not measurements."""
    allowed = {"0.10",    # the half-width the pre-registered power rule is stated at
               "0.9", "1.0", "0.3", "0.1",   # confidence-bin edges and axis ranges quoted in words
               "51.5", "74.5",               # Liu et al. 2023, abstract: other people's measurements
               "42.4"}                       # a figure quoted from the old README in order to retract it
    generated = "".join(p.read_text() for p in GEN.glob("*.tex"))
    gen_numbers = set(re.findall(r"\d+\.\d+", generated))
    # strip macros' own arguments, urls, and the bibliography-style numbering before scanning
    prose = re.sub(r"\\url\{[^}]*\}|\\pgfplotsset\{[^}]*\}", "", _prose())
    prose = re.sub(r"\\(?:ti[A-Z]\w*)\{\}", "", prose)
    typed = set(re.findall(r"(?<![\w.])\d+\.\d+(?![\w.])", prose))
    stray = {t for t in typed if t not in gen_numbers and t not in allowed}
    assert not stray, f"decimals typed into prose with no generated source: {sorted(stray)}"


def test_citations_resolve_and_the_bibliography_has_no_orphans() -> None:
    cited = set()
    for group in re.findall(r"\\cite[pt]?\*?\{([^}]+)\}", _prose()):
        cited.update(k.strip() for k in group.split(","))
    keys = set(re.findall(r"^@\w+\{([^,]+),", BIB.read_text(), re.M))
    assert not cited - keys, f"cited but not in refs.bib: {sorted(cited - keys)}"
    assert not keys - cited, f"in refs.bib but never cited: {sorted(keys - cited)}"


def test_bib_entries_carry_a_verifiable_id() -> None:
    """Every entry has an arXiv id, a DOI, or is a journal article with volume and pages."""
    for entry in re.split(r"\n(?=@)", BIB.read_text()):
        if not entry.startswith("@"):
            continue
        key = re.match(r"@\w+\{([^,]+),", entry).group(1)
        ok = "arXiv:" in entry or "doi" in entry or ("volume" in entry and "pages" in entry)
        assert ok, f"{key} has no arXiv id, DOI or volume and pages"


def test_vendor_language_is_scoped() -> None:
    """Statements about vendors describe the measurement. Names appear only where required; an
    unmeasured arm's vendor stays unnamed; no loaded words."""
    prose = _prose()
    assert "Exa" in prose
    for name in ("Ploid", "Apollo", "People Data Labs", "Clay", "ZoomInfo"):
        assert name not in prose, f"{name} must not appear in the paper"
    loaded = re.compile(r"\b(fraud\w*|scam\w*|deceiv\w*|decepti\w*|lying|liar|incompetent|shoddy|worthless|"
                        r"broken product|dishonest vendor)\b", re.I)
    assert not loaded.search(prose)
    assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", prose), "no email-shaped string in the paper"


def test_abstract_states_the_result_and_its_limits() -> None:
    abstract = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", _prose(), re.S).group(1)
    abstract = " ".join(abstract.split())
    for macro in ("tiAttRate", "tiNearRate", "tiFarRate", "tiCtlRate", "tiNearLo", "tiCtlHi"):
        assert f"\\{macro}{{}}" in abstract, macro
    for phrase in ("one endpoint", "one prompt", "drawn once", "third-party classifier", "I claim nothing"):
        assert phrase in abstract, phrase


def test_disclosure_paragraph_is_present() -> None:
    prose = _prose()
    for phrase in ("AI coding assistant", "commercial AI gateway", "CC BY 4.0", "MIT licence"):
        assert phrase in prose, phrase


@pytest.mark.skipif(not (shutil.which("tectonic") and shutil.which("pdftotext")),
                    reason="render check needs tectonic and pdftotext (run locally: make paper)")
def test_rendered_pdf_has_no_garbled_text(tmp_path: Path) -> None:
    """Build the PDF and read the text back, the check that caught vernier's eaten abstract."""
    for f in TEX.parent.iterdir():
        if f.is_file():
            shutil.copy(f, tmp_path / f.name)
    shutil.copytree(GEN, tmp_path / "generated")
    r = subprocess.run(["tectonic", "-X", "compile", "titer.tex"], cwd=tmp_path, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    txt = subprocess.run(["pdftotext", "-layout", str(tmp_path / "titer.pdf"), "-"],
                         capture_output=True, text=True).stdout
    for bad in ("(?)", "[?]", "Citation", "undefined", "Table ?", "Figure ?", "Section ?", "\\ti"):
        assert bad not in txt, bad
    m = ex.numbers()
    # the abstract's numbers survived rendering IN THE ABSTRACT (the same figures also appear in
    # Table 2, so a whole-document search would not notice an abstract that lost them)
    abstract_txt = " ".join(txt.split("Abstract", 1)[1].split("1 Introduction", 1)[0].split())
    for bad in ("tiAttRate", "tiNearRate", "{}"):
        assert bad not in abstract_txt, f"macro text leaked into the rendered abstract: {bad}"
    for key in ("tiAttRate", "tiNearRate", "tiFarRate", "tiCtlRate", "tiNearLo", "tiNearHi", "tiFarLo", "tiFarHi",
                "tiCtlLo", "tiCtlHi"):
        assert m[key] in abstract_txt, f"{key}={m[key]} missing from the rendered abstract"
    assert "95% Wilson" in abstract_txt
    # every table and figure rendered, and the references list is complete
    for cap in ("Table 1:", "Table 2:", "Table 3:", "Figure 1:", "Figure 2:", "Figure 3:"):
        assert cap in txt, cap
    n_refs = len(re.findall(r"^@\w+\{", BIB.read_text(), re.M))
    assert len(re.findall(r"^\s*\[\d+\]", txt, re.M)) == n_refs


def _result_numbers() -> set[str]:
    """Every four-decimal number the committed results can produce, in either spelling."""
    out: set[str] = set()

    def walk(x) -> None:
        if isinstance(x, float):
            out.add(f"{abs(x):.4f}")
        elif isinstance(x, str):
            out.update(re.findall(r"\d+\.\d{4}", x))
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    for p in (ROOT / "results").glob("*.json"):
        walk(json.loads(p.read_text()))
    g = ex.numbers()
    out.update(v for v in g.values() if re.fullmatch(r"\d+\.\d{4}", v))
    return out


#: Four-decimal figures in the README that are arithmetic on committed numbers and not stored anywhere.
README_DERIVED: dict[str, str] = {}


def test_readme_four_decimal_figures_trace_to_results() -> None:
    """The README's headline numbers are not transcribed: each four-decimal figure is in a results file
    or is a figure the exporter derives from one."""
    readme = (ROOT / "README.md").read_text()
    have = _result_numbers()
    missing = sorted({n for n in re.findall(r"(?<![\d.])\d\.\d{4}(?!\d)", readme)} - have - set(README_DERIVED))
    assert not missing, f"README figures with no artifact: {missing}"


def test_zenodo_metadata_is_built_from_the_paper() -> None:
    """The deposit can say nothing the paper does not: its abstract, references and ids are derived."""
    committed = json.loads((ROOT / ".zenodo.json").read_text())
    assert committed == ez.build(), "run scripts/export_zenodo.py"
    assert committed["creators"] == [{"name": "Theodoro, Caio", "orcid": "0009-0005-7343-981X"}]
    assert committed["license"] == "cc-by-4.0" and committed["upload_type"] == "publication"
    assert "Not peer reviewed." in committed["description"]
    n_bib = len(re.findall(r"^@\w+\{", BIB.read_text(), re.M))
    assert len(committed["references"]) == n_bib
    # every arXiv id the paper cites is a related identifier, and nothing else claims to be cited
    cited = {r["identifier"] for r in committed["related_identifiers"] if r["relation"] == "cites"}
    assert cited == {f"arXiv:{i}" for i in re.findall(r"arXiv:(\d{4}\.\d{4,5})", BIB.read_text())}


def test_citation_file_and_licences_agree() -> None:
    cff = (ROOT / "CITATION.cff").read_text()
    assert "license: MIT" in cff and "0009-0005-7343-981X" in cff
    assert (ROOT / "LICENSE").read_text().startswith("MIT License")
    assert "CC BY 4.0" in (ROOT / "README.md").read_text()
