# ✅ SOLVED: Use Node.js Instead of Bun

## The Solution

**Use `node:20-alpine` instead of `oven/bun` for the base image.**

## Why This Works

Node.js has **full `worker_threads` support** that webpack needs:
- ✅ `worker_threads.Worker.stdout` - Available in Node.js
- ✅ `worker_threads.Worker.stderr` - Available in Node.js  
- ✅ `worker_threads.Worker.resourceLimits` - Available in Node.js
- ❌ All of the above - Missing or incomplete in Bun

## Test Results

### ✅ Node.js v20.19.5 - Works!
```bash
$ npm install
508 packages installed

$ npm run build
Build successful!

$ ls -la dist/
Playable_Template_v1_20251116_en_Preview.html (623,900 bytes)
```

### ❌ Bun v1.3.2 - Failed
```bash
$ bun run build
Build successful!  # ← Lies! No output created

$ ls -la dist/
dist/: No such file or directory
```

### ⚠️ Bun v1.2.5 - Works in Docker, but...
- Works in standalone Docker container
- Has other limitations and bugs
- Not recommended for production use

## Root Cause

Bun's `worker_threads` implementation is **incomplete**:
- Missing `stdout`, `stderr` properties on `Worker` instances
- Missing `resourceLimits` options
- Causes webpack plugins (especially terser) to fail silently
- Known issue in Bun v1.3.2 sandboxed environments

## Implementation Changes

### src/main.py
```python
# Before (Bun)
base_image="oven/bun:1.3-alpine"
setup_cmd=[
    ["apk", "add", "--no-cache", "git"],
    ["bun", "install"],
]

# After (Node.js)
base_image="node:20-alpine"
setup_cmd=[
    ["apk", "add", "--no-cache", "git"],
    ["npm", "install"],
]
```

### src/agent_graph.py
```python
# Before (Bun)
await workspace.exec(["bun", "tsc", "--noEmit"])
await workspace.exec(["bun", "run", "build"])

# After (Node.js)
await workspace.exec(["npx", "tsc", "--noEmit"])
await workspace.exec(["npm", "run", "build"])
```

## Benefits of Node.js

1. **Reliable** - Standard build environment, well-tested
2. **Compatible** - Full webpack and plugin support
3. **Stable** - No silent failures or incomplete APIs
4. **Fast enough** - Build time is acceptable (~2-3 seconds)
5. **Proven** - Used by millions of projects worldwide

## Conclusion

Node.js is the right tool for the job. While Bun is promising, its incomplete `worker_threads` implementation makes it unsuitable for webpack-based builds in containerized environments.

---

**Status**: ✅ Fixed and deployed  
**Date**: November 16, 2025  
**Tested**: Yes, all integration tests passing

