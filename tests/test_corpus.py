

class TestEntityFilerExclusion:
    """A Section 16 reporting owner is not always a human.

    419 of 23,015 built tasks named a fund or an LLC. Asking a people-search
    index for the current employer of "Permira V L.P." is a guaranteed MISS
    that reads as a coverage failure. Three landed in the seed-11 n=40 draw:
    7.5 points of fabricated error rate, caught by the R001 pilot rule.
    """

    def test_corporate_forms_are_entities(self):
        from titer.corpus.name_norm import is_entity_name
        for n in ["Permira V L.P.2", "ARMISTICE CAPITAL, LLC", "GAZIT AMERICA INC",
                  "Warburg Pincus XI Partners, L.P.", "New Mountain Capital, L.L.C.",
                  "MacAndrews & Forbes Inc.", "D. E. Shaw Oculus Portfolios, L.L.C.",
                  "MHR Institutional Advisors III LLC", "AVENUE INTERNATIONAL, LTD."]:
            assert is_entity_name(n), n

    def test_people_with_corporate_sounding_surnames_are_kept(self):
        """The conservative half. These are real filers, not organisations."""
        from titer.corpus.name_norm import is_entity_name
        for n in ["HOLDING FRANK B JR", "TRUST MARTIN", "BRYANT HOPE HOLDING",
                  "Turk Joseph E Jr", "BANKS ROGER", "CHURCH STEVEN M",
                  "Cagnetta Andrew R. Jr.", "Hoagland Eleanor T.M."]:
            assert not is_entity_name(n), n

    def test_built_task_set_contains_no_entity_filers(self):
        import json
        from pathlib import Path
        from titer.corpus.name_norm import is_entity_name
        p = Path(__file__).resolve().parent.parent / "data" / "tasks.jsonl"
        if not p.exists():
            return
        bad = [json.loads(ln)["person_name_raw"] for ln in p.open()
               if is_entity_name(json.loads(ln)["person_name_raw"])]
        assert bad == [], f"{len(bad)} entity filers survived the build: {bad[:5]}"
