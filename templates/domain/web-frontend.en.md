# Domain Fragment: Web Frontend (web-frontend)

> T2 domain fragment · source: production | applies to: worker | spawn domain: web-frontend
> Injected into the spawn's task spec at dispatch (not identity-file content)

## Context Input (spawn reads from files)

- project structure explanation + component tree / route table (file references; never dump source into conversation)
- code paths (refs) of the target component/page
- design mock / interaction spec (if any)

## Execution Constraints

- the tech stack follows the project's locked versions (package.json = contract; dependency versions never change unless the spec requires it — a dependency change = R2)
- component reuse over new writing: grep the existing component library first
- styling follows the existing design tokens/conventions (consistency scorecard item)
- build verification: `build` passes + target page loads (scorecard carries the command output)
- artifact = file diff (patch/ref); never paste large code blocks into messages

## Acceptance Points (critic perspective)

- function: every interaction path reproducible (command/operation steps)
- boundaries: empty / error / loading — the three states checked
- regression: impact-surface grep (who references the changed component/util)
- performance surface: no new obvious blocking (bundle-size comparison, if a baseline exists)
