# DRAFT — outreach to Ploid

**Status: DRAFT. NOT SENT.** House rule inherited from `assay`: draft it, show
it, decide separately. Nothing goes out without an explicit decision.

**Before this is sent, one thing must be true and currently is not:** it links
to a public repository. If the repo is private the links are dead and the email
is unfalsifiable.

---

**Subject:** We measured what your `identity_verified` flag would need to mean

Hi —

I built an open instrument that measures whether a people-search provider's
claim about a person is *attested* by a public record, rather than judged by a
model. Everything is published: code, corpora, pre-registrations (hash-published
before the studies ran), and two formal retractions.

- Repo: https://github.com/caiotheodoro/titer
- Findings: https://huggingface.co/spaces/caiotheodoro/titer

**I want to be straight about Ploid specifically: I have no measurement of you.**
I ran three attempts and killed all three, because each was broken by a defect
in *my* harness — I put the company in the free-text query instead of your
documented `filters`, then filtered on the anchor employer in a way that forced
the answer. `docs/RETRACTIONS.md` R001 has the detail. The credits ran out before
I got a clean run, so no number about Ploid is claimed anywhere.

What I do have is an architectural observation from your docs, and one measured
result from a different provider that suggests it matters.

**The observation.** Your search filters are `title`, `seniority`, `company`,
`industry`, `location` — every one describes a person's *current* state. There
is no way to express *"the Jane Chen who was at Acme in 2019."* When a name
collides, the caller cannot hand over the one fact that would disambiguate. I
have logged this as an explicit **hypothesis**, not a finding
(`docs/DECISIONS.md` D029), together with the four-arm experiment that would
settle it. I did not have the credit to run it.

**The measured result.** On a different provider, given a person and a research
topic they have provably never published in — verified exhaustively against
OpenAlex — it affirmed the claim roughly **one time in six**, at a stated
confidence of 0.987. It confirmed *real* expertise 96% of the time. The failure
is asymmetric: it is bad at saying no.

**Why I think that is your opportunity rather than your problem.** Your
architecture already separates cheap search from a paid verify step, with
`identity_verified: false` until someone pays. That is the right shape, and most
of the market does not have it. What is missing is the *attestation chain* behind
the word "verified" — which record, from which registrar, filed when — and a
biographical input to disambiguate on.

The expert-sourcing market is where I would expect that to sell, and I have
written up both the case and the case against it in `docs/MARKET.md`, including
the part that argues you would be competing with buyers who deliberately own
their own attested supply.

If any of it is useful, I would rather run the Ploid arm properly than leave it
retracted. The harness and the task set are frozen and ready; it needs about $10
of credit. Either way the work is public and I am happy to be told where I have
it wrong.

— Caio

---

## Notes for the sender, not part of the email

- Do **not** claim any Ploid measurement. There is none.
- D029 is a hypothesis. If it is described as a finding anywhere in a reply
  thread, correct it immediately.
- If they grant credit, the run is pre-registered and the result gets published
  whichever way it goes. Say that up front.
- `docs/RETRACTIONS.md` is the strongest credibility artefact here. Link it
  rather than hiding it.
