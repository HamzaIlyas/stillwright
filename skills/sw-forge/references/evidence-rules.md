# Why forge demands evidence

Two findings shape this skill's rules. Both are public; check them before relaxing anything.

- **SkillsBench**, version 1 (https://arxiv.org/abs/2602.12670v1; 86 tasks across 11
  domains): curated skills raised the average pass rate by 16.2 points; skills the models
  wrote for themselves before each task averaged 1.3 points below the no-skill baseline, with
  one model (Opus 4.6) at +1.4. Later versions of the paper report larger losses for
  self-generated skills. The authors' reading: models cannot reliably author the procedural
  knowledge they benefit from consuming. Note the test covers skills written before a task,
  not skills distilled from a success afterwards, which is what forge does; treat that as
  untested rather than proven.
- **Rethinking self-evolving agent skills** (https://arxiv.org/abs/2608.02636): of 388
  candidate skills, 55 set a new validated best; across 14 settings, 11 selected an evolved
  skill and 9 improved final results, and validation and final results sometimes disagreed.
  The authors describe the process as sparse, validation-filtered search rather than steady
  improvement from more rounds; every selected skill came from feedback that included failed
  trajectories.

What other systems do, for comparison:

- Hermes Agent (https://hermes-agent.nousresearch.com/docs/user-guide/features/skills) stages agent-written skills for approval when `skills.write_approval` is on,
  prefers targeted patches over rewrites, and scans for dangerous patterns, but has no test
  before a skill is used.
- Prime Agent's continual harness (https://github.com/PrimeIntellect-ai/prime-agent, paper https://arxiv.org/abs/2605.09998) refines prompts, memories and skills only from trajectory
  evidence, stores the rationale and expected outcome with each change, and keeps a
  before-snapshot so any refinement can be rolled back; it does not evaluate before applying.
- ECC's continuous-learning-v2 (https://github.com/affaan-m/ECC/blob/main/skills/continuous-learning-v2/SKILL.md) turns observations into "instincts" with a confidence score
  that rises on repeat and falls on correction or disuse, promoted at 0.7; no test step.
- Anthropic's skill-creator (https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md) runs 2-3 prompts with and without the skill in parallel, grades
  with evidence, and keeps a human review in the loop.

Stillwright takes the test-before-install step from skill-creator, the evidence-and-rollback
record from Prime Agent, the decay rule from ECC, and the approval gate from Hermes.
