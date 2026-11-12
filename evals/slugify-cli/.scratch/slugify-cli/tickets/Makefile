# Written by `tickets.py init`. Run: make status | make tickets | make show NUM=02
TICKETS := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
TOOL    := python3 -I $(TICKETS)/tickets.py --dir $(TICKETS)

.PHONY: status tickets show

status:   ## one line per ticket: state, READY when unblocked
	@$(TOOL) status

tickets:  ## every ticket with its tasks: [x] done, [ ] open
	@$(TOOL) status --tasks

show:     ## one ticket and the briefs of its blockers: make show NUM=02
	@$(TOOL) show $(NUM)
