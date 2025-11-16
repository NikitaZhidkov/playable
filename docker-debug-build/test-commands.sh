#!/bin/sh
# Script to run inside the Docker container for systematic debugging

echo "==================================="
echo "PLAYABLE BUILD DEBUG TEST"
echo "==================================="

echo "\n1. Environment Info:"
echo "-----------------------------------"
echo "Bun version: $(bun --version)"
echo "Node modules: $(ls node_modules | wc -l) packages"
echo "Working directory: $(pwd)"
echo "User: $(whoami)"

echo "\n2. Template Files:"
echo "-----------------------------------"
ls -lh src/
ls -lh assets/

echo "\n3. Type Check (should work):"
echo "-----------------------------------"
bun tsc --noEmit
TYPE_CHECK_EXIT=$?
echo "Type check exit code: $TYPE_CHECK_EXIT"

echo "\n4. Build Attempt 1 - Standard:"
echo "-----------------------------------"
bun run build
BUILD1_EXIT=$?
echo "Build exit code: $BUILD1_EXIT"
ls -la dist/ 2>/dev/null || echo "❌ dist/ not found"

echo "\n5. Build Attempt 2 - With DEBUG:"
echo "-----------------------------------"
DEBUG=* bun run build 2>&1 | head -100

echo "\n6. Build Attempt 3 - Direct playable-scripts:"
echo "-----------------------------------"
./node_modules/.bin/playable-scripts build
BUILD3_EXIT=$?
echo "Direct build exit code: $BUILD3_EXIT"
ls -la dist/ 2>/dev/null || echo "❌ dist/ still not found"

echo "\n7. Check Permissions:"
echo "-----------------------------------"
touch test-write.txt && rm test-write.txt && echo "✅ /app is writable" || echo "❌ /app is NOT writable"

echo "\n8. Summary:"
echo "-----------------------------------"
echo "Type check: $([ $TYPE_CHECK_EXIT -eq 0 ] && echo '✅ PASS' || echo '❌ FAIL')"
echo "Build:      $([ -d dist ] && echo '✅ PASS' || echo '❌ FAIL')"
echo ""
echo "If build failed, try these manual commands:"
echo "  - DEBUG=webpack:* bun run build"
echo "  - strace bun run build 2>&1 | grep -i dist"
echo "  - cd /tmp && cp -r /app/* . && bun install && bun run build"

