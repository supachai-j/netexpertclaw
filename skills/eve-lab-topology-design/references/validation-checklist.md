# Design validation checklist (adapted from NetClaw's validation-workflow, Apache-2.0)

## Gate before build - confirm all, or surface what is unresolved
1. Domain classified. 2. Node list final. 3. Link list final. 4. No orphan nodes. 5. No isolated segments. 6. Redundancy level stated and accepted. 7. Forbidden adjacencies identified. 8. Image availability confirmed by the user. 9. Host RAM/CPU fit checked. 10. Scope confirmed.

## Final answer sections
Requirement summary; recommendations; image and platform choices; physical topology; logical/protocol topology; validation result (PASS/WARN/FAIL + resilience level); build plan; configuration plan (only if asked); risks and open questions.

## Checks
- Structure: every node has a link; every segment has two or more endpoints; the graph is connected; the link list matches the connectivity table.
- Roles: no host-to-core or access-to-internet link unless intentional and labelled; in leaf-spine, spines connect only to leaves; in provider labs, PE nodes connect only to the intended CE and P roles.
- Resilience: the redundancy claim matches the link list; articulation-point nodes and bridge links are named; peers in a redundancy group have equal uplinks.
- Protocols: routing coverage for every non-host node; redistribution points named; no obvious black holes. (Not checked by the tool.)

## Build-plan order (for the user to run in EVE-NG; this skill does not do it)
Create lab; confirm images; check host capacity; create nodes and verify; map interfaces; create networks; connect interfaces; verify topology; validate the exported .unl with the tool; start nodes; apply startup configs if in scope; verify connectivity.

## Config rules
Node name as hostname; state image/OS at the top of each config block; use a stated addressing plan; only requested protocols; use `<password>` placeholders, never fake secrets.
