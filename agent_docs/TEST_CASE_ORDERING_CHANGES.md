# Test Case Ordering and Retry Count Changes

## Summary of Changes

Three important improvements to test case validation logic:

### 1. ✅ Test Cases Run in Order (1 → 5)

**Problem:** Test cases were discovered but not guaranteed to run in sequential order.

**Solution:** Sort test case files after discovery to ensure they always run 1 → 5.

```python
# Discover test case files (at root level)
test_case_files = await state["workspace"].list_files("test_case_*.json")
# Sort test cases to ensure they run in order (1 -> 5)
test_case_files = sorted(test_case_files)
```

**Why it matters:** 
- Predictable execution order
- Test case 1 runs before test case 2, etc.
- Easier to debug failures

### 2. ✅ Stop on First Test Case Failure

**Problem:** System would run all test cases and collect all failures, wasting time and API costs.

**Solution:** Return immediately when any test case fails, stopping execution of remaining test cases.

```python
# Old behavior: Collect all failures
test_case_failures = []
for test_case in test_cases:
    if fails:
        test_case_failures.append(failure)  # Continue to next test

# New behavior: Stop on first failure
for test_case in test_cases:
    if fails:
        return {  # Return immediately, stop execution
            "test_failures": [failure],
            "retry_count": retry_count + 1
        }
```

**Why it matters:**
- **Save time:** Don't run remaining tests if first one fails
- **Save costs:** Fewer VLM API calls
- **Faster feedback:** Agent gets error immediately, can fix and retry
- **Clearer errors:** Only one failure at a time to focus on

### 3. ✅ Smart Retry Count Reset

**Problem:** Retry count kept incrementing even when fixing issues, eventually hitting max retries (5).

**Solution:** Reset retry count to 0 when passing a stage that previously failed.

#### Reset Scenarios:

**Scenario A: Pass Main VLM Validation After Failing**
```python
# If we failed main VLM validation before (retry_count > 0)
# and now we pass it → reset retry count to 0
if previous_retry_count > 0 and previous_failures:
    logger.info("Main VLM validation passed after failures - resetting retry count")
test_case_retry_count = 0
```

**Scenario B: Pass Test Case After Failing**
```python
# If this specific test case failed before and now passes → reset to 0
previous_failures = state.get("test_failures", [])
if any(test_case_name in str(failure) for failure in previous_failures):
    logger.info(f"Test case {test_case_name} passed after previous failure - resetting retry count")
    test_case_retry_count = 0
```

**Why it matters:**
- **Fair retry limits:** Each stage gets 5 attempts, not 5 total
- **Prevents premature failure:** Won't hit max retries if making progress
- **Better UX:** Agent can iterate on different issues without hitting limit

## Retry Count Flow Example

```
Attempt 1: Main VLM fails          → retry_count = 1
Attempt 2: Main VLM fails          → retry_count = 2
Attempt 3: Main VLM passes ✅      → retry_count = 0 (RESET!)
           test_case_1 fails       → retry_count = 1
Attempt 4: Main VLM passes ✅      
           test_case_1 fails       → retry_count = 2
Attempt 5: Main VLM passes ✅
           test_case_1 passes ✅   → retry_count = 0 (RESET!)
           test_case_2 fails       → retry_count = 1
Attempt 6: Main VLM passes ✅
           test_case_1 passes ✅
           test_case_2 passes ✅   → All done! 🎉
```

Without reset, this would have hit max retries (5) at attempt 5.

## Test Coverage

### New Tests (`tests/integration/test_test_case_ordering.py`)

**6 tests covering the new behaviors:**

1. ✅ `test_test_cases_run_in_order` - Verifies files sorted correctly (1→5)
2. ✅ `test_test_case_ordering_with_gaps` - Works with gaps (1,3,5)
3. ✅ `test_test_case_ordering_alphabetically_correct` - String sorting behavior
4. ✅ `test_natural_sorting_for_single_digits` - Single digits sort correctly
5. ✅ `test_maximum_five_test_cases_enforced` - Limit to 5 enforced
6. ✅ `test_retry_count_reset_logic` - Unit test for reset logic

**All tests passing:** 6/6 ✅

## Files Modified

- **`agent_graph.py`** - Main logic changes:
  - Sort test case files after discovery
  - Return immediately on first test case failure
  - Reset retry count when passing previously failed stages
  
- **`tests/integration/test_test_case_ordering.py`** - New test file:
  - Tests for ordering behavior
  - Tests for retry count reset logic

## Running the Tests

```bash
# Run ordering and retry tests
pytest tests/integration/test_test_case_ordering.py -v

# Run all test case validation tests
pytest tests/test_test_case_validation.py tests/integration/test_test_case_flow.py -v

# Run all tests
pytest tests/ -v
```

## Benefits Summary

| Change | Time Saved | Cost Saved | UX Improvement |
|--------|------------|------------|----------------|
| **Ordered execution** | Minimal | None | ✅ Predictable |
| **Stop on first failure** | ⚡ Significant | 💰 VLM API calls | ✅ Faster feedback |
| **Smart retry reset** | ⏱️ Avoids premature failure | 🔄 More attempts | ✅ Better iteration |

## Implementation Notes

- **Sorting:** Uses Python's built-in `sorted()` which is stable and reliable
- **Immediate return:** Breaks out of loop on first failure, no need to check remaining tests
- **Reset logic:** Checks previous failures in state to determine if reset is needed
- **Logging:** Clear log messages indicate when retry count resets and why

## Edge Cases Handled

1. **No test cases:** Still returns error (require 1-5)
2. **More than 5 test cases:** Limits to first 5 after sorting
3. **Test cases with gaps:** Works correctly (1, 3, 5 runs in that order)
4. **No previous failures:** Reset logic doesn't break, just stays at 0

