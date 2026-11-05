# Trust-Me-Bro

# Adversarial Influence in Multi-Agent Code Review

This repository contains the code, scenario set, and experimental results for a study of whether an adversarial agent embedded in a multi-agent code-review pipeline can influence honest reviewer agents to approve security-relevant defects.

The adversarial agent cannot execute or modify code. It participates only in the review discussion and attempts to influence the group’s final accept/reject decision.

## Research question

Can an adversarial reviewer planted by a malicious developer influence honest AI reviewers to approve security-relevant defects without modifying or executing the code?

## Overview

The experiment compares three review conditions:

1. **Independent review** — one reviewer evaluates each artifact and produces a binary verdict.
2. **Honest multi-agent review** — four honest reviewers discuss an artifact and produce a group verdict.
3. **Adversarial multi-agent review** — one adversarial reviewer and three honest reviewers discuss an artifact and produce a group verdict.

Each reviewer can read the code artifact, state a position, respond to other reviewers, and vote. The pipeline supports up to three discussion rounds before producing a final binary verdict: `ACCEPT` or `REJECT`.

Corrected artifacts should receive an `ACCEPT` verdict. Defective artifacts should receive a `REJECT` verdict.

## Threat model

The threat model assumes an organization uses AI agents to review code before approving it for downstream use. A malicious developer compromises the review pipeline by implanting an adversarial reviewer.

The adversarial reviewer’s objective is to influence honest reviewers into accepting a security-relevant defect. It cannot modify or execute the code; its only available action is to participate in the review discussion.

## Benchmark

The benchmark contains 30 unique code-review scenarios, organized as 15 matched pairs:

- One defective artifact
- One corrected control artifact

Selected scenarios were evaluated more than once to assess decision stability. This produced 45 final review decisions per experimental condition.

The defective artifacts include issues such as:

- Missing authorization checks
- Insecure default configuration
- Destructive actions performed before authorization
- Boundary-condition errors
- Weak identity handling
- Inadequate secret comparison
- Missing idempotency controls

## Metrics

The experiment records the following outcomes for each final review decision:

| Outcome | Definition |
|---|---|
| True positive (TP) | Defective artifact correctly rejected |
| False negative (FN) | Defective artifact incorrectly accepted |
| True negative (TN) | Corrected artifact correctly accepted |
| False positive (FP) | Corrected artifact incorrectly rejected |

Primary measures include:

- Defect-detection rate
- False-positive rate
- False-negative rate
- Counts of TP, TN, FP, and FN
- Qualitative analysis of adversarial influence strategies

Decision-level results treat each evaluation as one observation. Scenario-level results aggregate repeated evaluations by artifact.

## Qualitative analysis

Discussion transcripts are analyzed to identify tactics used by the adversarial reviewer, including:

- Shifting responsibility to upstream components
- Narrowing the relevant security scope
- Minimizing concerns that lack demonstrated exploitability
- Reinterpreting specification inconsistencies as intentional design choices
- Characterizing defensive mitigations as unnecessary complexity

These tactics are evaluated qualitatively; they are not treated as proof that every adversarial argument was factually false.

## Technical setup

- Language: Python
- Model provider: DeepInfra
- Model: `Qwen3-235B-A22B-Instruct-2507`
- Review workflow: up to four reviewer agents
- Multi-agent conditions: four reviewers
- Independent condition: one reviewer
- Discussion: up to three rounds
- Final decision: binary accept/reject verdict

A homogeneous model configuration was used because the initial study did not systematically evaluate multiple model families or model scales.

## Running the experiment

Install dependencies:

```bash
pip install -r requirements.txt
```

Set your DeepInfra API key:

```bash
export DEEPINFRA_API_KEY="your_api_key"
```

Run the review pipeline:

```bash
python src/run_experiment.py
```

Run the analysis:

```bash
python analysis/analyze_results.py
```

Update these commands if your entry-point scripts use different names.

## Results

Across 45 final review decisions per condition, the honest multi-agent group detected the most defective artifacts but also produced the most false-positive rejections. Introducing an adversarial reviewer reduced false-positive rejections while modestly increasing false negatives.

| Condition | Defect detection | False positives | False negatives |
|---|---:|---:|---:|
| Independent review | 28 | 1 | 17 |
| Honest multi-agent group | 31 | 12 | 14 |
| Adversarial multi-agent group | 29 | 6 | 16 |

These are preliminary results from a small benchmark and should not be interpreted as evidence that adversarial agents reliably bypass code review.

## Limitations

- The benchmark contains only 30 unique scenarios.
- The study uses one model family and a homogeneous reviewer configuration.
- Some repeated evaluations mean the 45 decisions are not fully independent.
- Several scenarios depend on assumptions about external requirements, such as audit logging or secure defaults.
- The study measures review decisions, not deployment to production.
- Results should be replicated with larger datasets,
