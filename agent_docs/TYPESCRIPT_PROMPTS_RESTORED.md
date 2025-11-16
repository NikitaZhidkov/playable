# TypeScript Prompts and Code - RESTORED

## Summary
All changes that were lost due to `git restore` have been successfully restored.

## ✅ Changes Restored

### 1. **src/prompts.py** - TypeScript-Specific Instructions

#### window.loadTestCase (lines 77-99)
- ✅ Added TypeScript implementation instructions
- ✅ Shows how to add method to Game class
- ✅ Shows how to expose globally via index.ts
- ✅ Proper TypeScript typing: `public loadTestCase(data: any): void`

#### File Placement Clarifications
- ✅ **TEST_CASE_CREATE_REQUIREMENTS** (line 133): "WORKSPACE ROOT (same level as package.json, NOT in src/)"
- ✅ **CONFIG_FILE_CREATE_REQUIREMENTS** (line 158): "WORKSPACE ROOT (same level as package.json, NOT in src/)"
- ✅ **TEST_CASE_MODIFY_REQUIREMENTS** (line 272): "WORKSPACE ROOT (same level as package.json)"

#### TypeScript Config Loading Pattern (lines 195-229)
- ✅ Added TypeScript interface `GameConfig`
- ✅ Added typed async function: `async function loadConfig(): Promise<GameConfig>`
- ✅ Proper TypeScript fetch pattern with `./config.json`

#### Test Case Instructions
- ✅ Added note: "The build system automatically makes them accessible to the built game"
- ✅ Clarified file locations throughout

---

### 2. **src/agent_graph.py** - Build Process Updates

#### Post-Build File Copying (lines 291-359)
- ✅ Get workspace files list: `workspace_files = await workspace.ls(".")`
- ✅ Copy critical files (fail fast if missing):
  - config.json
  - MANIFEST.json
- ✅ Copy test case files (flexible 1-5):
  - Check existence: `if test_file in workspace_files`
  - Only copy if exists
  - Count: `test_cases_copied`
- ✅ Validate at least 1 test case exists (fail if 0)

#### HTML File Handling (lines 329-351)
- ✅ Find HTML files in dist/
- ✅ Validate exactly 1 HTML file (fail if != 1)
- ✅ Copy to index.html for testing
- ✅ Update workspace in state

#### Test Container Setup (lines 388-391)
- ✅ Changed from `directory(".")` to `directory("dist")`
- ✅ Comment: "Use built game from dist/ directory (after TypeScript compilation)"

---

## Key Principles Applied

### ✅ Fail Fast Philosophy
- **No try-except blocks** - errors propagate naturally
- Critical files (config.json, MANIFEST.json) fail immediately if missing
- HTML validation fails build if != 1 file

### ✅ Explicit File Checking
- Check existence first: `if test_file in workspace_files`
- No defensive try-except around optional files
- Clear error messages when validation fails

### ✅ Flexible Test Cases (1-5)
- Loop checks 1-5 test cases
- Only copies those that exist
- Requires at least 1 (fails if 0)
- No rigid "must have 5" requirement

### ✅ Self-Contained Build Output
- Everything needed is in `dist/`
- Config files copied to dist/
- Test cases copied to dist/
- HTML accessible as index.html
- Test container gets complete package

---

## File Structure After Build

```
workspace/
  src/               ← TypeScript source
    Game.ts
    index.ts
    index.html
    index.css
  assets/            ← Game assets
  config.json        ← At workspace root
  MANIFEST.json      ← At workspace root
  test_case_*.json   ← At workspace root
  package.json
  tsconfig.json

After Build:
  dist/
    Playable_*.html        ← Built bundle (versioned name)
    index.html             ← Copy for testing (NEW)
    config.json            ← Copied (NEW)
    MANIFEST.json          ← Copied (NEW)
    test_case_1.json       ← Copied (NEW)
    test_case_2.json       ← Copied if exists (NEW)
    ... etc
```

---

## Testing Flow

1. ✅ Build TypeScript → creates `dist/Playable_*.html`
2. ✅ Copy config/test files → into `dist/`
3. ✅ Create `dist/index.html` → from built HTML
4. ✅ Copy entire `dist/` to test container
5. ✅ Test accesses files at `/app/index.html`, `/app/config.json`, etc.

---

## Benefits

1. ✅ **Clear TypeScript guidance** - Developers know exactly how to implement features
2. ✅ **Proper file placement** - No confusion about where files go
3. ✅ **Self-contained builds** - Everything needed is in dist/
4. ✅ **Consistent testing** - Files always at expected locations
5. ✅ **Fail fast** - Problems are immediately visible
6. ✅ **Flexible** - Works with 1-5 test cases

---

## Date Restored
November 16, 2025

## Status
✅ **All changes successfully restored and verified**

