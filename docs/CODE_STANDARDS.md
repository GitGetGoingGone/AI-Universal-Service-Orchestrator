# Code Standards & Conventions

## Python

### Style

- **PEP 8** as baseline
- **Black** for formatting (line length 100)
- **Ruff** for linting and import sorting
- **Type hints** on all public functions and class methods

### Configuration

- `pyproject.toml` - Black and Ruff config
- Run: `black .` and `ruff check .` (or `ruff format .`)

### Docstrings

Use **Google style**:

```python
def search_products(query: str, limit: int = 20) -> list[dict]:
    """Search products by name.

    Args:
        query: Search term (e.g. 'flowers', 'chocolates').
        limit: Maximum number of results to return.

    Returns:
        List of product dicts with id, name, price, etc.

    Raises:
        ValidationError: If query is empty.
    """
```

### Naming

- **Variables/functions**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private**: `_leading_underscore`

## TypeScript / JavaScript

### Style (when added)

- **ESLint** with recommended rules
- **Prettier** for formatting
- **camelCase** for variables and functions
- **PascalCase** for components and types

### Naming

- **Components**: `PascalCase` (e.g. `ProductCard`)
- **Hooks**: `use` prefix (e.g. `useProducts`)
- **Files**: Match export (e.g. `ProductCard.tsx`)

## Database

- **Tables**: `snake_case` (e.g. `order_items`)
- **Columns**: `snake_case` (e.g. `created_at`)
- **Indexes**: `idx_{table}_{column(s)}`

## Code Review Checklist

- [ ] Tests pass
- [ ] Lint passes (`ruff check .`, `black --check .`)
- [ ] No secrets or credentials
- [ ] Error handling for external calls
- [ ] Type hints on new code
- [ ] Docstrings on public APIs
