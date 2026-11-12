FROM node:20-slim AS build

WORKDIR /srv

# Copy dependency files first for Docker layer caching
COPY add-ai-frontend/package.json add-ai-frontend/package-lock.json ./

# Install dependencies inside the container
RUN npm ci

# Copy application source
COPY add-ai-frontend/ .

# Vite environment variable
ARG VITE_API_BASE_URL=/
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Make Vite executable
RUN chmod +x node_modules/.bin/vite

# Build Nuxt/Vite application
RUN npm run build


FROM node:20-slim

WORKDIR /srv

COPY --from=build /srv/.output ./.output

EXPOSE 3000

ENV PORT=3000

CMD ["node", ".output/server/index.mjs"]
