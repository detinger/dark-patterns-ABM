# Technology in Society — Manuscript Revision Notes

**Date:** 2026-06-28  
**Branch:** main (uncommitted)  
**Files changed:** `main.tex`, `references.bib`, `declarations.tex`, `.gitignore`, `manuscript/.gitignore`  
**New untracked files:** DOCX export, Morris SA outputs, network comparison data, `s1_morris.py`

---

## 1. Title

**Before:**
> Simulating the Long-Term Impact of Dark Patterns on User Trust: A Network-Based Agent-Based Model

**After:**
> Dark Patterns as a Value-Destroying Strategy: An Agent-Based Network Model of Trust, Social Contagion, and Platform Sustainability

Updated in: `\title`, `\shorttitle`, `references.bib` header comment.  
Rationale: previous title was identical to a conference submission; new title leads with the paper's core economic finding and is more distinctive.

---

## 2. Author Block

| Item | Before | After |
|------|--------|-------|
| First author | Dejana Pivac | Darko Etinger |
| Corresponding author | Dejana Pivac | Darko Etinger |
| ORCID | none | `0000-0003-4444-7202` (Etinger) |
| Co-first authorship footnote | none | "These authors contributed equally to this work." |
| Short author string | D. Pivac and D. Etinger | D. Etinger and D. Pivac |

Implementation: `\cormark[1]` + `\fnmark[1]` on both authors; `\fntext[1]` added; `\ead[orcid]` added.

---

## 3. New Analytical Content

### 3.1 Morris Elementary-Effects Sensitivity Analysis (§4.6)
Global sensitivity screening of **7 parameters simultaneously** (360 model runs: 15 trajectories × 4 levels × 3 seeds per point):

- `γ` dark pattern intensity  
- `α` exposure-to-trust coefficient  
- `δ` exposure-to-harm coefficient  
- `κ` social influence strength  
- `q` customer support quality  
- `θ_T` churn trust weight  
- `θ_H` churn harm weight  

**Key results:** `γ` dominates both outputs by 3.2-3.4×; all signed effects point in expected directions; `α`, `κ`, `θ_H` are interaction-dominated (σ > μ*). Conclusions are robust to simultaneous perturbation of all seven parameters.

**New files:**
- `manuscript/figures/fig_morris.pdf` — μ*/σ scatter plot
- `manuscript/tables/table4_morris.tex` — full parameter rankings
- `replication-package/s1_morris.py` — analysis script
- `replication-package/data/processed/morris_cache_X.npy`
- `replication-package/data/processed/morris_cache_Y.npz`
- `replication-package/data/processed/morris_mu.csv`

### 3.2 Network Topology Sensitivity Test (§4.6)
Medium-intensity scenario re-run on a **Barabási-Albert scale-free network** (N=500, k̄=8, m=4), 20 seeds. All four tipping points trigger in the same qualitative order in every seed; BA produces lower churn (46.8% ± 2.1% vs 53.3% ± 2.3%) and higher residual trust (0.274 ± 0.018 vs 0.215 ± 0.011) due to near-zero local clustering. Establishes Watts-Strogatz baseline as a conservative upper bound.

**New file:** `replication-package/data/processed/s3_network_compare.npz`

---

## 4. New and Expanded Manuscript Sections

### 4.1 Section 2.5 — Trust Dynamics and ABM (expanded)
Prior version name-dropped Dellarocas (2006), Deffuant (2000), Goldenberg (2001) without explanation. Replaced with 1-2 sentences per work explaining what each modelled and why it falls short, closing with a crisp gap statement: *"no prior model couples a platform's strategic design choices, heterogeneous user behavioral traits, and the resulting WOM-mediated trust-economy feedback loop in a single computational framework."*

### 4.2 Section 3.2 — User Agents (1 sentence added)
Added justification for the 50/30/20 type distribution: grounded in Luguri & Strahilevitz (2021) finding that dark patterns remain effective at scale; flagged as a fixed assumption whose variation preserves qualitative results.

### 4.3 Section 3.4 — Trust and Harm Dynamics (1 paragraph added)
Added explicit justification that coefficients (α=0.22, δ=0.18) are illustrative rather than fitted, and explained why per-step caps (0.035, 0.04) are kept small—so regime shifts arise from accumulation and contagion rather than single-exposure shocks.

### 4.4 Section 3.5 — Social Contagion (1 paragraph added)
Added empirical motivation for the negative/positive WOM asymmetry, citing Baumeister et al. (2001) negativity bias. Explains that gating positive WOM conservatively encodes this bias; relaxing it would slow but not qualitatively alter dynamics.

### 4.5 Section 3.8 — Network Structure (expanded from 1 sentence to 1 paragraph)
Added justification for WS parameter choices (p=0.08 in transition regime; k̄=8 for platform-scale diffusion). Explained why high clustering is the load-bearing structural assumption, cross-referencing the BA topology test in §4.6.

### 4.6 Section 4.3 — Per-Pattern Analysis (1 paragraph added)
Added mechanistic explanation of the harm ranking:
- **Forced trial** most harmful: high gain weight + moderate detectability = prolonged exposure window
- **Drip pricing** second: highest base harm but shorter extraction window once detected
- **Hard cancellation** least: highest detectability causes fast exit before harm accumulates

Counter-intuitive policy implication: higher detectability reduces systemic harm, so *disclosure mandates may outperform post-hoc removal*.

### 4.7 Section 4.5 (Intensity Comparison) — 1 sentence added
Added threshold sensitivity check for Trust Collapse threshold (varied 0.40-0.55): crossing step shifts by at most 8 steps but qualitative ordering is preserved across all seeds.

### 4.8 Section 4.6 — Limitations (1 paragraph added)
Expanded the single-platform assumption from one sentence to a full paragraph, arguing it is a *deliberate scoping choice* corresponding to quasi-monopoly contexts, making current results a *conservative lower bound* on churn consequences.

### 4.9 Section 5.1 — Self-Reinforcing Destruction Loop
Added reference to new Figure 8 (causal loop diagram).

### 4.10 Section 5.3 — Heterogeneous Vulnerability and Lock-In (2 paragraphs added)
**Para 2 — Welfare implication:** The most harmed users are those who *stay*, not those who leave. Naive user lock-in maps onto Rossi (2024)'s situational/dispositional vulnerability framing; conventional protected-group categories are structurally blind to this harm.

**Para 3 — Composition effect:** As activists/skeptics churn, remaining population shifts toward naive users. WOM volume falls (activists are prolific propagators), making platform reputation appear to stabilize while harm deepens — a *measurement artefact* that will mislead regulators using complaint rates as a proxy.

### 4.11 Section 5.4 — Implications for Regulatory Policy (expanded from 3 bullets to 3 full paragraphs)
1. **Intensity thresholds vs binary bans:** Even intensity 0.20 crosses two tipping points; graduated regulation (analogous to decibel limits) would better track the harm curve than DSA Article 25's binary frame.
2. **Contagion externalities as public harm:** Dark patterns harm users never directly exposed; individual-redress mechanisms (opt-out, complaint, litigation) are structurally inadequate for network-propagated harms.
3. **Extractive Divergence as mandatory disclosure metric:** Framed in economic terms platforms already track; proposed as a leverage-ratio-style leading indicator requiring mandatory reporting above a size threshold.

### 4.12 Section 6 — Conclusion (complete rewrite)
Previous conclusion paraphrased the abstract. New conclusion:
- Opens with the reframe: *detection problem → systemic dynamics problem*
- Para 2: "no safe deployment level" finding, Extractive Divergence as regulatory metric
- Para 3: three-direction structured future-work agenda (empirical calibration → multi-platform competition → adaptive regulatory dynamics), closing with reference to the open replication package

---

## 5. New Figure

### Figure 8 — Self-Reinforcing Destruction Loop (TikZ, §5.1)
Causal loop diagram showing the full harm pipeline (Dark Pattern Intensity → Exposure → Harm → Trust Erosion → Negative WOM → Churn → Reputation → Revenue Loss) with a dashed social-contagion feedback arrow from Negative WOM back to Trust Erosion. Generated in-document via TikZ (no external file dependency).

Required preamble additions: `\usepackage{tikz}`, `\usetikzlibrary{positioning,arrows.meta}`.

---

## 6. New References Added

| Key | Citation |
|-----|---------|
| `morris1991` | Morris, M.D. (1991). Factorial Sampling Plans for Preliminary Computational Experiments. *Technometrics*, 33(2), 161-174. |
| `baumeister2001` | Baumeister et al. (2001). Bad Is Stronger Than Good. *Review of General Psychology*, 5(4), 323-370. |

---

## 7. Declarations Update (`declarations.tex`)

**CRediT statement:**
- "Funding acquisition" added to Etinger's roles
- "Software" confirmed for both authors

**Funding section** (was: *"This research did not receive any specific grant..."*):
> This research was supported by Juraj Dobrila University of Pula through the internal research projects *Application of Metaheuristic Optimization in Collaborative Robotic Systems* META-KOLA-BOT (Grant No. IIP_010144) and *Generative Artificial Intelligence in Modeling and Execution of Distributed Enterprise Software Information Systems* GENESIS (Grant No. IIP_010136).

---

## 8. Data and Code Availability (`main.tex`)

GitHub URL was incorrect (`dark-matters-ABM` → `dark-patterns-ABM`). Zenodo placeholder removed; statement now follows the Elsevier template for repositories without DOIs. CoMSES reference removed pending actual archival.

**Current statement points to:** `https://github.com/detinger/dark-patterns-ABM`

---

## 9. Output Files

| File | Pages | Size | Notes |
|------|-------|------|-------|
| `manuscript/main.pdf` | 17 | 562 KB | Up from 14 pages |
| `manuscript/Dark Patterns as a Value-Destroying Strategy.docx` | — | 197 KB | Pandoc export; TikZ/macros resolve partially |

---

## Items Still Pending (pre-submission)

- [ ] Zenodo archival — only if requested by editor/reviewers; GitHub link is sufficient per Elsevier policy
- [ ] Confirm GenAI declaration in `declarations.tex` reflects actual writing practice
- [ ] Resolve `ersoy2026` missing `pages` field in BibTeX (pre-existing warning, not blocking)
