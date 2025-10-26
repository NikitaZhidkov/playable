# Test Case Prompt Improvements

## Overview

Enhanced system prompts and feedback messages to guide the LLM agent in creating better test cases and debugging them more effectively.

## Key Improvements

### 1. ✅ Test Case Ordering (Simple → Complex)

**Added to:** `SYSTEM_PIXI_GAME_DEVELOPER_PROMPT` and `SYSTEM_PIXI_FEEDBACK_PROMPT`

**Guidance:**
```
Test cases should be ordered from SIMPLE to COMPLEX:
- test_case_1: Initial/start state (SIMPLEST)
- test_case_2: Basic interaction (simple gameplay)
- test_case_3: Mid-game state with typical gameplay
- test_case_4: Win/loss condition
- test_case_5: Edge cases or complex scenarios (MOST COMPLEX)
```

**Why it matters:**
- Identifies basic issues first before testing complex scenarios
- Agent can debug incrementally
- Simpler tests are more reliable and easier to fix
- If test_case_1 fails, you know there's a fundamental problem

### 2. ✅ Don't Modify Passing Tests

**Added to:** `SYSTEM_PIXI_FEEDBACK_PROMPT`

**Guidance:**
```
CRITICAL - Test Case Iteration Strategy:
- If a test case PASSED, DO NOT rewrite or modify it
- Only work on FAILED test cases
```

**Why it matters:**
- Prevents breaking working tests
- Focuses agent's attention on actual problems
- Reduces unnecessary churn
- Saves time and API costs

### 3. ✅ Think About Test Correctness

**Added to:** `SYSTEM_PIXI_FEEDBACK_PROMPT` and feedback messages

**Guidance:**
```
When a test case fails, THINK CAREFULLY:
* Is the game wrong? (Fix the game code)
* Is the test wrong? (Fix the test case)
* Is expectedOutput incorrect or too vague? (Update the test)
* Does the test describe a real, visible situation? (If not, rewrite the test)
```

**Questions to ask:**
- Does the expectedOutput describe what SHOULD be visible on screen?
- Is the expected output realistic and achievable?
- Is the test case state valid for this game?
- Am I testing visual elements or internal state?

**Why it matters:**
- Sometimes the test itself is wrong, not the game
- Prevents infinite loops of "fixing" correct code to match bad tests
- Encourages critical thinking about test quality
- Leads to more meaningful test cases

### 4. ✅ Enhanced Feedback Messages

**Updated:** All error feedback messages in `agent_graph.py`

#### Missing expectedOutput
```
Each test case MUST include an "expectedOutput" field that describes what should be VISIBLE on screen.

Example:
"expectedOutput": "Score displays 100, player is at position (200, 300), 3 enemies visible"

Make it specific and visual - the VLM needs to verify this from a screenshot.
```

#### Test Case Loading Errors
```
Common issues:
1. window.loadTestCase function not found → Add it to your game.js
2. Test case has invalid state data → Check the test case JSON matches your game's MANIFEST.json structure
3. Game doesn't pause after loading → Ensure you stop game loops/animations in loadTestCase

Remember: This is test_case_1 - keep it SIMPLE if it's test_case_1 or test_case_2.
```

#### VLM Validation Failure
```
Before fixing, think carefully:
1. Is the GAME wrong? → Fix the game code
2. Is the TEST wrong? → Fix the test case expectedOutput or game state
3. Is the test case describing something that's actually visible on screen?

Remember: Test cases should go from SIMPLE (test_case_1) to COMPLEX (test_case_5).
If other test cases passed, don't modify them - only fix this failed test.
```

#### Technical Errors
```
This is a technical error. Before fixing, consider:
1. Is the test case JSON valid? Check for syntax errors
2. Does the test case state make sense for the game?
3. Is the test trying to set impossible values?

Remember: Start with SIMPLE states. If this is test_case_1, it should be the easiest possible state to test.
```

### 5. ✅ Test Case Quality Guidelines

**Added to:** `SYSTEM_PIXI_GAME_DEVELOPER_PROMPT`

**Guidelines:**
- Make sure expectedOutput describes REAL, VISIBLE elements
- Don't test internal state that isn't visually represented
- Be specific: "Score displays 100" not "Game state is correct"
- Think: Can VLM verify this from a screenshot?

## Example Flow with Improved Prompts

### Scenario: Agent creates game with 3 test cases

**Initial creation:**
```json
// test_case_1.json (SIMPLE)
{
  "score": 0,
  "expectedOutput": "Game shows initial state with score 0"
}

// test_case_2.json (MEDIUM)
{
  "score": 50,
  "level": 2,
  "expectedOutput": "Game shows score 50, level 2 indicator visible"
}

// test_case_3.json (COMPLEX)
{
  "score": 1000,
  "level": 10,
  "powerups": ["shield", "speed"],
  "expectedOutput": "Game shows score 1000, level 10, shield and speed powerup icons visible"
}
```

### Scenario: test_case_2 fails

**Old behavior:**
- Agent might rewrite all 3 tests
- Might not question if the test itself is correct
- Generic error message

**New behavior with improved prompts:**

1. **Feedback message guides thinking:**
   ```
   test_case_2 failed: Expected 'score 50, level 2 visible' but VLM observed 'score 50, no level indicator'
   
   Before fixing, think carefully:
   1. Is the GAME wrong? → Maybe level indicator isn't implemented
   2. Is the TEST wrong? → Maybe level indicator doesn't exist yet
   ```

2. **Agent analyzes:**
   - "test_case_1 passed (score works) ✓"
   - "test_case_2 failed because level indicator doesn't exist"
   - "Should I add level indicator to game, or fix the test?"

3. **Agent decides:**
   - If level indicator should exist → Fix game code
   - If level indicator not needed → Update test expectedOutput
   - Leaves test_case_1 untouched (it passed!)

## Benefits

### For Agent
- ✅ Clear guidance on test case strategy
- ✅ Structured approach to debugging
- ✅ Reduces confusion about what to fix
- ✅ Prevents unnecessary changes to working tests

### For Development
- ✅ Better test quality (specific, visual, verifiable)
- ✅ Faster iterations (focus on failures only)
- ✅ More reliable tests (simple → complex ordering)
- ✅ Fewer false positives (agent questions test correctness)

### For User
- ✅ Fewer wasted retry attempts
- ✅ Better test coverage
- ✅ More meaningful test cases
- ✅ Faster bug detection

## Files Modified

1. **`playbook.py`**
   - Enhanced `SYSTEM_PIXI_GAME_DEVELOPER_PROMPT` with ordering and quality guidelines
   - Enhanced `SYSTEM_PIXI_FEEDBACK_PROMPT` with iteration strategy and critical thinking prompts

2. **`agent_graph.py`**
   - Improved all test case failure feedback messages
   - Added context-specific guidance for each error type
   - Included reminders about test case ordering in errors

## Testing

The improvements are transparent to the test suite - they guide the LLM's behavior through prompts and feedback messages, not by changing code logic.

All existing tests still pass:
- ✅ Unit tests: 12/12
- ✅ Integration tests: 12/12
- ✅ Total: 24/24

## Usage

These improvements are automatic - the LLM agent will receive the enhanced prompts and feedback messages when:

1. **Creating a game:** Receives guidance on test case ordering and quality
2. **Fixing issues:** Receives structured feedback on what to check
3. **Iterating:** Reminded to only touch failed tests

## Examples of Good vs Bad Tests

### ❌ Bad Test Case
```json
{
  "internalState": "complex_state_123",
  "expectedOutput": "Game state is correct"
}
```
**Problems:**
- Tests internal state (not visible)
- Vague expectedOutput
- VLM can't verify from screenshot

### ✅ Good Test Case
```json
{
  "score": 100,
  "playerX": 200,
  "playerY": 300,
  "enemiesCount": 3,
  "expectedOutput": "Score text displays '100' at top, player sprite visible at center-left, 3 enemy sprites visible on screen"
}
```
**Good because:**
- Tests visible elements
- Specific expectedOutput
- VLM can verify everything mentioned
- Describes actual visual layout

## Future Improvements

Potential additions based on usage:
- Template examples for common test cases
- Checklist for test case quality
- Automated test case suggestions based on game type
- Test case difficulty scoring


