# Use Node.js instead of Bun (has full worker_threads support for webpack)
FROM node:20-alpine

# Install git
RUN apk add --no-cache git

# Set working directory
WORKDIR /app

# Copy the template
COPY template/ /app/

# Don't install here - we'll do it after volume mount
# This way node_modules will be in the mounted directory

# Keep container running for debugging
CMD ["tail", "-f", "/dev/null"]

