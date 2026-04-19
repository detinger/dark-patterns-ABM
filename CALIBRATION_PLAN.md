# Calibration Plan

This document turns the current Dark Patterns ABM parameters into a concrete calibration workflow.

The goal is not to tune values by intuition alone. Instead, each parameter should be linked to:

- an empirical construct
- a recommended data source
- an estimation method
- a validation target

## Calibration strategy

Use a three-layer approach:

1. Micro-calibration
   Fit user-level traits and decision-rule coefficients from survey, experiment, audit, or behavioral data.

2. Meso-calibration
   Fit interaction and social diffusion parameters from review visibility, complaint diffusion, and peer-effect evidence.

3. Macro-validation
   Check whether simulated trust, churn, reputation, and revenue trajectories resemble real or benchmarked aggregate outcomes.

## Recommended empirical sources

- Survey data
  Use for trust, switching cost, complaint propensity, perceived fairness, and digital literacy.

- Experimental or vignette data
  Use for causal effects of dark patterns on trust, perceived harm, and switching intent.

- Product audit datasets
  Use for prevalence of forced trials, hard cancellation, drip pricing, and similar interface patterns.

- Platform analytics or panel data
  Use for churn, retention, support recovery, and long-run revenue relationships.

- Review and social media data
  Use for negative WOM prevalence, persistence, and visibility.

## Parameter map

### Scenario and environment controls

| Parameter | Meaning | Primary source | Estimation method | Calibration target / note |
| --- | --- | --- | --- | --- |
| `num_users` | Simulated population size | Study design choice | Scenario design, not statistical calibration | Match the scale needed for computational tractability and the empirical population slice being modeled |
| `network_type` | Graph family (`small_world`, `scale_free`, `random`) | Social network literature or platform communication structure evidence | Model selection by best structural fit | Choose the graph family that best matches clustering, path length, and degree concentration in the target setting |
| `avg_degree` | Average number of user ties | Social graph data, communication/contact surveys | Match sample mean degree | Calibrate to average interaction or visibility neighborhood size |
| `rewire_prob` | Small-world randomness | Network studies | Moment matching or graph-fit search | Match clustering coefficient and path length jointly |
| `max_steps` | Horizon length | Study design, panel time span | Scenario design | Map each step to a real time unit first, then set horizon accordingly |
| `seed` | Random seed | None | Reproducibility control | Not calibrated; used for deterministic replay and replication |

### Platform policy and intervention parameters

| Parameter | Meaning | Primary source | Estimation method | Calibration target / note |
| --- | --- | --- | --- | --- |
| `dark_pattern_intensity` | Overall aggressiveness of manipulation | Product audits, expert coding, prevalence datasets | Normalize a composite index to `[0,1]` | Build from observed count and severity of manipulative patterns per product or scenario |
| `pattern_forced_trial` | Forced trial enabled | Audit data | Binary scenario flag | Usually scenario-defined; turn on when the product family actually uses the pattern |
| `pattern_hard_cancel` | Hard cancellation enabled | Audit data | Binary scenario flag | Same as above |
| `pattern_drip_pricing` | Drip pricing enabled | Audit data | Binary scenario flag | Same as above |
| `customer_support_quality` | Capacity of support to repair trust | Survey, service-quality studies, support satisfaction data | Normalize satisfaction or response-quality score to `[0,1]` | Higher values should correspond to shorter resolution times and better user-rated support outcomes |
| `adaptive_platform` | Whether platform changes strategy when outcomes worsen | Organizational / strategic assumption | Scenario flag | Usually scenario-defined rather than statistically calibrated |

### Social diffusion and observability

| Parameter | Meaning | Primary source | Estimation method | Calibration target / note |
| --- | --- | --- | --- | --- |
| `social_influence_strength` | Magnitude of trust erosion from observed negative signals | Peer-effect studies, review effect experiments | Regression or experimental effect-size mapping | Fit to marginal effect of exposure to negative reviews on trust or switching intent |
| `review_visibility` | Probability that negative sentiment reaches a neighbor | Platform UX data, review-impression data, user survey | Visibility / impression rate estimate | Map to how often users actually see peer complaints or reviews |

### User trait distributions

These are especially suitable for direct calibration because the model now samples them with Beta distributions.

| Parameter | Meaning | Primary source | Estimation method | Calibration target / note |
| --- | --- | --- | --- | --- |
| `trust_baseline_mean` | Mean pre-exposure user trust | Trust surveys | Fit mean of bounded response scale | Use baseline trust before presenting dark-pattern scenarios |
| `trust_baseline_sd` | Dispersion of baseline trust | Trust surveys | Fit standard deviation, then convert to Beta | Use the same instrument as `trust_baseline_mean` |
| `digital_literacy_mean` | Mean digital literacy | Digital literacy scales, online skills surveys | Fit mean of normalized scale | Normalize survey scores to `[0,1]` |
| `digital_literacy_sd` | Dispersion of digital literacy | Digital literacy scales | Fit standard deviation | Keep paired with the same scale as above |
| `manipulation_sensitivity_mean` | Mean sensitivity to manipulative design | Vignette survey or experiment | Fit mean rating of perceived manipulation / discomfort | Best estimated from exposure to concrete dark-pattern examples |
| `manipulation_sensitivity_sd` | Dispersion of manipulation sensitivity | Vignette survey or experiment | Fit standard deviation | Important for heterogeneous reactions |
| `social_activity_mean` | Mean propensity to share experiences | Social posting / review behavior data, self-report | Fit mean share/review propensity | Map to probability or normalized activity index |
| `social_activity_sd` | Dispersion of social activity | Same as above | Fit standard deviation | Needed to create heavy posters and quiet users |
| `complaint_propensity_mean` | Mean tendency to complain publicly or privately | Complaint behavior surveys, support logs | Fit mean complaint propensity | Can combine self-report and observed complaint rate |
| `complaint_propensity_sd` | Dispersion of complaint propensity | Same as above | Fit standard deviation | Useful for reproducing uneven complaint participation |
| `switching_cost_mean` | Mean cost/friction of leaving the platform | Switching-cost surveys, lock-in studies | Fit mean of normalized switching-friction score | Include financial, procedural, habit, and social lock-in if relevant |
| `switching_cost_sd` | Dispersion of switching cost | Same as above | Fit standard deviation | Important for heterogeneous churn resistance |

### Exposure prevalence and severity

| Parameter | Meaning | Primary source | Estimation method | Calibration target / note |
| --- | --- | --- | --- | --- |
| `forced_trial_exposure_prob` | Base probability of forced-trial exposure | Product audit or user journey logging | Event frequency estimate | Estimate exposure per step before multiplication by `dark_pattern_intensity` |
| `forced_trial_severity` | Harmfulness of forced trial when exposed | Experiment, vignette survey, expert elicitation | Normalize average perceived harm / trust loss | Map to bounded severity in `[0,1]` |
| `hard_cancel_exposure_prob` | Base probability of hard-cancel exposure | Product audit or cancellation-flow data | Event frequency estimate | Use proportion of sessions encountering a hard-cancel obstacle |
| `hard_cancel_severity` | Harmfulness of hard cancellation | Experiment, vignette survey, complaint narratives | Normalize average perceived harm | Usually expected to be high because it appears at the exit stage |
| `drip_pricing_exposure_prob` | Base probability of drip-pricing exposure | Price-flow audits | Event frequency estimate | Measure share of purchase flows with late price revelation |
| `drip_pricing_severity` | Harmfulness of drip pricing | Experiment, vignette survey | Normalize average perceived harm or fairness loss | Often especially strong for fairness perceptions |

### Trust, harm, and recovery mechanism coefficients

| Parameter | Meaning | Primary source | Estimation method | Calibration target / note |
| --- | --- | --- | --- | --- |
| `alpha_exposure_to_trust` | Direct trust-loss coefficient from exposure | Controlled experiment | Regress post-exposure trust change on exposure severity | This should reproduce average trust decline per exposure |
| `beta_support_recovery` | Recovery effect from support quality | Customer service datasets, support experiments | Regress trust recovery on support quality | Fit partial recovery rather than full reversal |
| `delta_exposure_to_harm` | Harm increase per exposure | Harm/perceived burden survey, experiment | Regress harm score on exposure severity | Useful to anchor cumulative harm dynamics |
| `gamma_social_trust_loss` | Trust-loss from social contagion | Review effect studies, peer-exposure experiments | Fit marginal effect of observed peer negativity on trust | This is the key meso-calibration parameter |

### Churn model parameters

These should ideally be calibrated together from the same churn or switching dataset.

| Parameter | Meaning | Primary source | Estimation method | Calibration target / note |
| --- | --- | --- | --- | --- |
| `theta0` | Churn intercept (currently -7.0) | Retention / panel dataset | Logistic regression intercept | Baseline churn when predictors are neutral. Current value gives ~0.08% weekly healthy churn (~92% 2yr retention) |
| `theta_trust` | Effect of trust loss on churn | Retention / panel dataset, switching survey | Logistic regression coefficient | Fit effect of lower trust on exit probability |
| `theta_harm` | Effect of accumulated harm on churn | Same as above | Logistic regression coefficient | Harm should independently raise churn odds. Note: harm now saturates logistically at 1.0 |
| `theta_social` | Effect of negative WOM on churn | Same as above | Logistic regression coefficient | Fit contagion-mediated exit risk |
| `theta_switching_cost` | Protective effect of switching cost | Same as above | Logistic regression coefficient | Higher switching cost should reduce churn probability |

### Tipping-point rules

These are not part of `DEFAULTS`, but they should also be calibrated if you want the threshold logic to be evidence-based.

| Rule | Meaning | Primary source | Estimation method | Calibration target / note |
| --- | --- | --- | --- | --- |
| Trust Collapse threshold (`0.50`) | Persistent low-trust regime | Survey + retention breakpoints | Threshold search / breakpoint detection | Fit where downstream churn accelerates materially |
| Social Contagion threshold (`0.22`) | Persistent negative WOM regime | Review / complaint propagation data | Breakpoint or changepoint analysis | Fit where peer negativity starts spreading faster |
| Churn Cascade threshold (`0.35`) | Persistent user-loss regime | Cohort retention data | Threshold search | Fit where loss becomes self-reinforcing or hard to reverse |
| Extractive Divergence rule (`gap >= 20%`, churn `>= 0.15`) | Short-term extraction outpaces sustainable value | Revenue-retention panel data | Joint breakpoint optimization | Fit where revenue still grows short-run but long-run value deteriorates |
| Persistence window (`5 steps`) | Protection against one-step noise | Time aggregation choice + validation | Stability criterion tuning | Choose the shortest window that avoids false positives |

### New mechanics parameters (v1.2.0)

| Parameter | Meaning | Current value | Calibration note |
| --- | --- | --- | --- |
| `BETA_SHAPE` | Beta distribution shape for trait sampling | 5.0 | Higher values concentrate traits around type midpoints |
| `EXPOSURE_BUILDUP_STEPS` | Exposures before full harm | 3 | Fit to observed habituation/sensitisation timelines |
| `INITIAL_HARM_FRACTION` | Harm fraction on first exposure | 0.2 | First encounter is 20% as harmful as steady-state |
| `HARM_DAMPENING_FACTOR` | Recovery dampening by accumulated harm | 1.0 | At harm=0.85 recovery drops to 15% effectiveness |
| `HARM_DAMPENING_CAP` | Maximum dampening (floor on recovery) | 0.85 | Recovery never drops below 15% |
| `NATURAL_ATTRITION_PROBABILITY` | Background churn per agent per step | 0.0001 | ~0.01%, independent of dark patterns |
| `HIDDEN_EXTRACTION_MULTIPLIER` | Revenue multiplier for undetected exposures | 1.5 | Undetected dark patterns extract 50% more |
| `REPUTATION_FLOOR` | Minimum reputation on 0-100 scale | 5.0 | Even worst platforms retain baseline presence |
| `INITIAL_CUMULATIVE_REVENUE` | Starting revenue before dark patterns | 10,000 | Platform already has traction |
| `trust_resilience` (per type) | Fraction of trust loss dampened | naive: 0.30-0.50, skeptic: 0.00-0.10, activist: 0.00-0.05 | Fit to vignette responses per user archetype |

## Concrete calibration workflow

### Phase 1: Build a calibration table

For each parameter, record:

- target construct
- dataset name
- variable name
- transformation to `[0,1]` if needed
- estimation method
- uncertainty interval

### Phase 2: Fit directly observed quantities

Start with:

- trait means and standard deviations
- pattern prevalence rates
- support quality proxy
- review visibility

These are the easiest to estimate and will stabilize the rest of the model.

### Phase 3: Fit causal mechanism coefficients

Estimate:

- `alpha_exposure_to_trust`
- `delta_exposure_to_harm`
- `gamma_social_trust_loss`
- `beta_support_recovery`

Prefer experiments, vignette studies, or panel designs over simple cross-sectional correlations.

### Phase 4: Fit churn coefficients jointly

Use switching or retention microdata to fit:

- `theta0`
- `theta_trust`
- `theta_harm`
- `theta_social`
- `theta_switching_cost`

This is best done with logistic or discrete-time hazard models.

### Phase 5: Validate macro behavior

After micro-calibration, compare simulated outputs to empirical targets:

- average retention curve
- time to major trust decline
- complaint / review intensity
- revenue-retention divergence
- proportion of high-harm scenarios that trigger a tipping point

If the micro-level parameters fit but macro dynamics do not, tune the interaction and threshold parameters before changing the trait distributions.

## Minimum viable empirical package

If you need a realistic thesis workflow without assembling a giant proprietary dataset, the smallest practical combination is:

- one survey on trust, switching cost, complaint propensity, and digital literacy
- one vignette experiment exposing respondents to dark-pattern scenarios
- one audit dataset coding prevalence of forced trials, hard cancellation, and drip pricing
- one benchmark retention or churn dataset for the churn regression layer

That package is usually enough to justify a first serious calibration pass.

## Recommended outputs to save during calibration

- fitted parameter table with confidence intervals
- codebook showing survey question to parameter mapping
- sensitivity analysis around each fitted parameter
- goodness-of-fit comparison between simulated and empirical macro outcomes
- tipping-point validation plots

## Suggested next implementation step

Create a machine-readable file such as `calibration_targets.csv` with these columns:

- `parameter`
- `construct`
- `source_type`
- `dataset`
- `variable`
- `estimation_method`
- `target_value`
- `lower_bound`
- `upper_bound`
- `notes`

That will make it much easier to connect empirical work back into the model later.
