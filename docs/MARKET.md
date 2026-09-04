# MARKET — where an attestation layer would sell, and why it might not

Desk research, 2026-09-03. **This document contains no measurement.** Everything
in it is sourced from public material; nothing here was tested by this
repository, and the section that argues against the thesis is given equal weight
because it is the stronger half.

## The question

`titer` measures whether a provider's claim about a person is attested. Who
would pay for that?

## The case for expert sourcing

AI-data companies buy verified domain experts at scale, and the money is real
and compounding:

| Company | Signal |
|---|---|
| **Mercor** | ~$2B gross annualised revenue by June 2026, doubled in six months; $10B valuation; 30,000+ experts at >$85/hr average |
| **Micro1** | $500M gross run rate Aug 2026, 5× in eight months |
| **Handshake AI** | 0 → ~$1B annualised in ~15 months |
| **Surge AI** | ~$1.2B 2024 revenue, bootstrapped |
| **AfterQuery** | $300M → ~$3.2B valuation in ~5 months |

Frontier labs are reported at **~$1B/year each** on human data. Referral
bounties for a verified expert hire run **$250–$15,000**, which is the implicit
market price of sourcing one — and the number `CONTRACTS.md` A5 uses to justify
the `expert_sourcing` cost profile.

The incumbent expert networks are stalling: GLG's share fell from 51% to 24%
over a decade on roughly flat ~$650M revenue, while API-first challengers
(NewtonX, CleverX) proved the motion works.

## The case against — read this part first

**1. The winners won by *owning* attested supply, and say so publicly.**
Handshake's moat is 500,000 PhDs verified through **university registrar
integration** — `.edu` plus registrar, so credentials are institution-attested
rather than self-reported. Mercor sources >60% of expert hires by referral.
Micro1 built its own sourcing agent. A 3B-profile index is precisely the
commodity these companies have deliberately de-commoditised.

**2. The acute pain is verification, not discovery.** Suspected North Korean
operatives worked through Mercor on stolen credentials, in some cases producing
data for US labs. A March 2026 breach exfiltrated identity and biometric
dossiers and drew class actions. One vendor study flagged 38.5% of 19,368 AI
interviews for cheating — though that vendor sells anti-cheating tooling, so
treat it as directional. **Nobody in this market says they cannot find PhDs.**

**3. No public evidence that any of ten major buyers purchases third-party
people data.** Not one. That is either a gap in the research or a budget line
that does not exist, and only customer conversations settle it. It is the
difference between selling into a market and creating one.

**4. A competitor is already executing this exact GTM.** HeroHunt.ai sells a
"1B-reach people-search API" and is content-marketing into this segment.

**5. The published market sizing is unusable.** Analyst totals for AI training
data run $3–8B — *smaller than the combined revenue of the vendors inside them*
(Mercor + Surge + Handshake + Scale alone exceed it). These numbers must not
appear in a pitch; a sophisticated buyer will reject them on sight.

## What the evidence actually supports

Not "sell people search to expert platforms" — they build that, and it is the
commodity half.

**Handshake's moat is this repository's Tier A / Tier B distinction operating as
a business.** Attested-not-self-reported is worth roughly $1B of annualised
revenue to someone. That is the strongest external validation the method has,
and it points at a narrower product than an index:

> **Institution-attested verification at API speed** — registrars, licensing
> boards, publication records, employment filings — with the attestation chain
> exposed rather than collapsed into a boolean.

The measured finding is consistent with the need: a general-purpose provider
affirms claims about topics a person has never published in roughly one time in
six, at 98.7% stated confidence. An expert platform buying that signal at face
value admits a fake expert every sixth time it asks.

## Caveat on custody

The Mercor breach is a warning about *being the party that holds identity data*.
A verification layer that points at public evidence — a DOI, a filing, a
registrar record — rather than taking custody of biometrics is on the safer side
of that incident, and that is a product argument as much as an ethical one.

## Sources

Funding and revenue: TechCrunch, CNBC, BusinessWire, Dealroom, SiliconANGLE,
Sacra, Lenny's Newsletter. Fraud and breach: Forbes, HR Dive, Biometric Update,
Hausfeld. Expert networks: Inex One, GLG's 2021 S-1. Market sizing: Grand View,
Fortune Business Insights — cited to show the disagreement, not to rely on them.
