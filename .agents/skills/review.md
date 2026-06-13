# Skill: Code Review

## Trigger
Use when asked to "review", "check", "audit", or "inspect" code or a PR.

---

## Review Checklist

### Correctness
- [ ] Logic correct for happy path and edge cases
- [ ] No off-by-one errors
- [ ] All exceptions caught and handled
- [ ] async/await used correctly (no missing awaits)
- [ ] No race conditions in concurrent code

### Security
- [ ] No hardcoded credentials
- [ ] All user input validated/sanitized
- [ ] No path traversal possible
- [ ] SQL queries parameterized (no injection)
- [ ] No sensitive data in logs

### Performance
- [ ] No N+1 queries
- [ ] Heavy operations are async
- [ ] No unnecessary data fetching
- [ ] Caching used where appropriate

### Code Quality
- [ ] Functions are single-responsibility
- [ ] No code duplication (DRY)
- [ ] Names are descriptive
- [ ] Comments explain WHY, not WHAT
- [ ] Cyclomatic complexity < 10

### Testing
- [ ] Tests exist for all new code
- [ ] Edge cases covered
- [ ] Mocks used correctly (external calls only)
- [ ] Test names describe the scenario

### Architecture
- [ ] Follows patterns in ARCHITECTURE.md
- [ ] No circular imports
- [ ] Modules properly decoupled
- [ ] No abstraction leaks across module boundaries

---

## Output Format

```
## Review: [filename or PR #number]

✅ Good:
- [specific positive observation]

⚠️ Issues:
- [file:line] SEVERITY: [description]
  Fix: [concrete fix]

🔴 Critical (block merge):
- [issue]

Verdict: APPROVE / REQUEST_CHANGES
```

## Severity Levels
- 🔴 Critical — security vulnerability, data loss risk, crash
- 🟠 Major — logic error, missing error handling, perf issue
- 🟡 Minor — style, naming, missing docstring
- ℹ️ Suggestion — optional improvement

## Rules
- Cite file:line for every issue
- Separate "must fix" from "nice to have"
- Approve only when all Critical and Major issues resolved
- Don't suggest changes outside the PR scope
