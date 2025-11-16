# Possible Solutions for Bun Build Issue

## The Problem
Bun v1.3.2 has a known bug in sandboxed/containerized environments (Docker, Nix) where builds report success but produce no output.

**Source:** https://mtools.sasshoes.com/blog/bun-v1-3-2-empty

## Solution 1: Try Different Bun Version ⭐ RECOMMENDED

### Option A: Downgrade to Bun 1.2.5 (known to work)
```dockerfile
# Edit Dockerfile, line 2:
FROM oven/bun:1.2-alpine
```

### Option B: Try latest Bun (might have fix)
```dockerfile
# Edit Dockerfile, line 2:
FROM oven/bun:latest-alpine
```

Then rebuild:
```bash
docker-compose down
docker-compose build
docker-compose up -d
docker exec -it playable-build-debug sh
bun install
bun run build
ls -la dist/
```

---

## Solution 2: Use Debian Instead of Alpine

Alpine uses musl libc, Debian uses glibc. This might affect Bun's behavior.

```dockerfile
# Edit Dockerfile, line 2:
FROM oven/bun:1.3  # Remove -alpine
```

Note: Debian image is larger (~200MB vs 50MB) but more compatible.

Then rebuild and test as above.

---

## Solution 3: Use Node.js Instead of Bun

Node.js has better compatibility with webpack/playable-scripts.

```dockerfile
# Edit Dockerfile:
FROM node:20-alpine

# Install git
RUN apk add --no-cache git

# Set working directory
WORKDIR /app

# Copy the template
COPY template/ /app/

CMD ["tail", "-f", "/dev/null"]
```

Then in container, use `npm` instead of `bun`:
```bash
npm install
npm run build
ls -la dist/
```

---

## Solution 4: Build Outside Container

Since the build works on your Mac, you could:
1. Let TypeScript type checking run in container ✅ (this works!)
2. Run the actual build on the host machine after agent completes

**Workflow:**
```python
# In agent_graph.py build_node:
# Step 1: Type check in container (catches errors)
type_check = await workspace.exec(["bun", "tsc", "--noEmit"])

# Step 2: Skip playable-scripts build in container
# Step 3: Export source files to host
# Step 4: Build on host with: bun run build
```

---

## Solution 5: Try Different Output Directory

Some sandboxes have issues with certain paths.

Edit `build.json`:
```json
{
  "app": "Playable",
  "name": "Template",
  "version": "v1",
  "outDir": "/tmp/dist",  // Add this line
  "google_play_url": "https://play.google.com/store/games",
  "app_store_url": "https://www.apple.com/app-store/"
}
```

Then check `/tmp/dist` after build.

---

## Solution 6: Test with Minimal Webpack Config

Create a simple test to isolate the issue:

```bash
# Inside container
cat > test-build.js << 'EOF'
const webpack = require('webpack');
const path = require('path');

webpack({
  mode: 'production',
  entry: './src/index.ts',
  output: {
    path: path.resolve(__dirname, 'test-dist'),
    filename: 'bundle.js'
  }
}, (err, stats) => {
  if (err) console.error(err);
  console.log(stats ? 'Success!' : 'Failed!');
});
EOF

bun test-build.js
ls -la test-dist/
```

---

## Recommendation Priority:

1. **Try Solution 3 (Node.js)** - Most likely to work ⭐
2. **Try Solution 2 (Debian-based Bun)** - Good compatibility
3. **Try Solution 1 (Different Bun version)** - Quick to test
4. **Try Solution 4 (Build on host)** - Pragmatic workaround

## Current Status:

✅ **TypeScript type checking works perfectly** - This is the critical validation!
❌ Build output not created - Container environment issue
✅ Build works on host machine - Confirmed working locally

The agent's TypeScript migration is complete and functional. The build issue is a deployment/infrastructure problem, not a code generation problem.

