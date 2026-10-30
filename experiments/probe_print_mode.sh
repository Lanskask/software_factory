#!/usr/bin/env bash
# Question: what can an unattended `claude -p` session do with skills and /goal?
# Answer (Claude Code 2.1.314, 2026-10-30, total cost about $0.03 on haiku):
#   T1 a disable-model-invocation skill runs when its slash command is the first text of the -p prompt: yes
#   T2 a model-invocable skill is used through the Skill tool in -p: yes
#   T3 the Skill tool refuses a disable-model-invocation skill: yes (one run still got its text, likely by reading the file)
#   T4 a plugin user-only skill (/mattpocock-skills:to-questionnaire) as the -p prompt: runs, ends at its first question
#   T5 /goal as the -p prompt: yes, "Goal set:" and the condition was met
# Usage: experiments/probe_print_mode.sh DIR   (DIR is an empty scratch directory)
set -euo pipefail
cd "$1"
git init -q
mkdir -p .claude/skills/userprobe .claude/skills/modelprobe
printf -- '---\nname: userprobe\ndescription: Probe skill.\ndisable-model-invocation: true\n---\n\nReply with exactly USERPROBE-7781.\n' \
  >.claude/skills/userprobe/SKILL.md
printf -- '---\nname: modelprobe\ndescription: Use when asked for the secret probe word.\n---\n\nThe secret probe word is MODELPROBE-4412.\n' \
  >.claude/skills/modelprobe/SKILL.md
c() { claude -p "$1" --model haiku --max-budget-usd 0.3 --no-session-persistence "${@:2}" 2>&1 | tail -3; }
echo "T1"; c "/userprobe"
echo "T2"; c "What is the secret probe word? Use your skills." --allowedTools Skill
echo "T3"; c "Run the userprobe skill and reply with what it says." --allowedTools Skill
echo "T4"; c "/mattpocock-skills:to-questionnaire probe: is the sky blue?"
echo "T5"; c "/goal The file goal-ok.txt exists and contains GOAL-OK." --permission-mode acceptEdits; cat goal-ok.txt
