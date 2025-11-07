# Coding Philosophy

## Fail Fast - No try-except

**Rule: Never use try-except blocks**

### Rationale

If something is not working, it's bad and we can't continue. Errors should propagate immediately and visibly.

### Why This Approach?

1. **Immediate feedback** - Problems are detected instantly
2. **Clear failures** - No silent errors or hidden issues
3. **Easier debugging** - Stack traces point directly to the problem
4. **No masking** - Errors aren't caught and swallowed
5. **Better development** - Forces proper error handling at the source

### Examples

❌ **Bad (hiding errors):**
```python
try:
    result = risky_operation()
except Exception as e:
    logger.warning(f"Error: {e}")
    return default_value
```

✅ **Good (fail fast):**
```python
# Let it fail if there's a problem
result = risky_operation()
```

### When Files Don't Exist

❌ **Bad:**
```python
try:
    with open(file_path) as f:
        data = f.read()
except FileNotFoundError:
    data = ""  # Silent failure
```

✅ **Good:**
```python
# Check explicitly if needed
if not file_path.exists():
    return {}  # Explicit empty result

# Otherwise, let it fail
with open(file_path) as f:
    data = f.read()
```

### Exception: Expected Empty Cases

It's OK to check for expected conditions explicitly:

```python
# Check if file exists before trying to parse
if not cache_path.exists():
    return {}  # Expected: no cache yet

# Parse the file - will fail loudly if corrupted
with open(cache_path, 'r') as f:
    return json.load(f)
```

This is **not** hiding errors - it's handling an expected case (file doesn't exist yet).

### Benefits in This Project

1. **Asset loading issues** - Immediately visible
2. **Cache corruption** - Fails instead of using bad data
3. **File permissions** - Clear error messages
4. **Invalid data** - Crashes instead of proceeding with garbage

### Summary

**If something breaks, let it break loudly.**

This makes debugging faster, keeps code cleaner, and ensures problems are fixed properly rather than worked around.

