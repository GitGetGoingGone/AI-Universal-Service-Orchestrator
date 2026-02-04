# Git Workflow & Branching Strategy

## Branch Naming

| Prefix | Use |
|--------|-----|
| `feature/` | New features (e.g. `feature/MODULE-1-product-search`) |
| `fix/` | Bug fixes (e.g. `fix/health-check-state`) |
| `chore/` | Maintenance (e.g. `chore/update-deps`) |
| `docs/` | Documentation only |

## Commit Messages

Use **Conventional Commits**:

```
<type>(<scope>): <description>

[optional body]
```

**Types**: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`

**Examples**:
- `feat(discovery): add product search endpoint`
- `fix(middleware): use getattr for request.state`
- `docs: add code standards`

## Pull Request Process

1. Create branch from `main`
2. Make changes, commit with conventional format
3. Push and open PR
4. Fill out PR template
5. Request review
6. Address feedback
7. Merge (squash for feature branches)

## Merge Strategy

- **Feature branches**: Squash merge (single commit to main)
- **Release branches**: Merge commit (preserve history)
