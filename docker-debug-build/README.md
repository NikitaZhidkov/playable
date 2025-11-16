# Docker Build Debug Environment

This folder contains everything needed to reproduce and debug the `playable-scripts` build issue in a Docker container.

## Setup

### 1. Build the Docker image

```bash
cd docker-debug-build
docker-compose build
```

### 2. Start the container

```bash
docker-compose up -d
```

### 3. Connect to the container

```bash
docker exec -it playable-build-debug sh
```

## Inside the Container

Once connected, you're in `/app` with the template already set up.

### Check the environment

```bash
# Check Bun version
bun --version

# Check installed dependencies
ls -la node_modules/ | wc -l

# Check template files
ls -la
ls -la src/
ls -la assets/
```

### Run TypeScript type check (this works!)

```bash
bun tsc --noEmit
echo "Exit code: $?"
```

### Run the build (this is where it fails)

```bash
# Try basic build
bun run build

# Check if dist/ was created
ls -la dist/ 2>/dev/null || echo "dist/ not found"

# Try with verbose webpack output
DEBUG=webpack:* bun run build

# Try with NODE_ENV
NODE_ENV=production bun run build

# Check playable-scripts version
cat node_modules/@smoud/playable-scripts/package.json | grep version
```

### Debug webpack directly

```bash
# Check if webpack is available
which webpack

# Try running webpack directly (if it exists)
npx webpack --version

# Check playable-scripts CLI
cat node_modules/@smoud/playable-scripts/cli/index.js | head -50
```

### Compare with host machine

Exit the container and run on your macOS:

```bash
cd template
bun install
bun run build
ls -la dist/
```

## What to Look For

1. **Does the build print "Build successful!"?**
   - If NO: webpack is not running or failing silently
   
2. **Are there any error messages?**
   - Check stdout and stderr carefully
   
3. **Does dist/ get created?**
   - If NO: webpack compilation never completes
   
4. **Is there a difference in node_modules/?**
   - Compare package versions between container and host

5. **File system permissions?**
   - Check if Alpine has issues writing to `/app/dist/`

## Potential Fixes to Try

### Option 1: Different Node/Bun version
```bash
# Exit container and edit Dockerfile
FROM oven/bun:1.2-alpine  # or FROM node:20-alpine
```

### Option 2: Run webpack directly
```bash
# Install webpack globally
bun add -D webpack webpack-cli

# Try building with webpack directly
npx webpack --config node_modules/@smoud/playable-scripts/core/webpack.config.js
```

### Option 3: Check Alpine compatibility
```bash
# Try Debian-based image instead
FROM oven/bun:1.3  # (no -alpine)
```

### Option 4: Permissions
```bash
# Check if /app is writable
touch /app/test.txt && rm /app/test.txt && echo "Writable!" || echo "Not writable"

# Try building in /tmp
cd /tmp
cp -r /app/* .
bun install
bun run build
ls -la dist/
```

## Cleanup

```bash
# Stop and remove container
docker-compose down

# Remove image
docker rmi playable-build-debug
```

## Notes

- The template in `docker-debug-build/template/` is a copy, so you can modify it without affecting the original
- Changes you make inside the container to `/app` will be reflected in `template/` due to volume mounting
- TypeScript type checking works perfectly in this environment
- Only the `playable-scripts build` step fails to create `dist/`

