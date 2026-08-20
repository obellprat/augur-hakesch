FROM node:23-bookworm-slim AS build

ARG DATABASE_URL=${DATABASE_URL}

ENV DATABASE_URL=${DATABASE_URL}

WORKDIR /app

COPY CHANGELOG.md /CHANGELOG.md
COPY src/frontend/package.json ./package.json
COPY src/frontend/package-lock.json ./package-lock.json
COPY src/frontend/scripts ./scripts
COPY src/frontend/prisma ./prisma

# deb.debian.org (Fastly) is unreachable from some WSL/Docker IPv6 setups.
# Debian's CloudFront mirror works over HTTP without needing ca-certificates first.
RUN set -eux; \
    find /etc/apt -type f \( -name '*.list' -o -name '*.sources' \) \
      -exec sed -i 's|http://deb.debian.org|http://cdn-aws.deb.debian.org|g' {} +; \
    apt-get update -o Acquire::Retries=5; \
    apt-get install -y --no-install-recommends python3 make g++ git; \
    rm -rf /var/lib/apt/lists/*

# registry.npmjs.org often ECONNRESET on WSL/Docker IPv6. Prefer IPv4, retry, and
# limit parallel sockets so the registry does not drop the connection mid-read.
ENV NODE_OPTIONS=--dns-result-order=ipv4first
RUN npm config set fetch-retries 5 \
    && npm config set fetch-retry-mintimeout 20000 \
    && npm config set fetch-retry-maxtimeout 120000 \
    && npm config set fetch-timeout 300000 \
    && npm config set maxsockets 3 \
    && (npm ci \
        || (sleep 5 && npm ci) \
        || (sleep 15 && npm ci) \
        || (sleep 30 && npm ci) \
        || (sleep 45 && npm ci))

COPY src/frontend .

# Host node_modules must not overwrite the image install. Rebuild native
# addons after COPY so they match this image's Node ABI (currently 23 / 131).
RUN npm rebuild better-sqlite3 --build-from-source

RUN npm run prepare
RUN npx prisma generate
RUN npm run build

FROM node:23-bookworm-slim AS run

ENV NODE_ENV=production

WORKDIR /app

RUN apt-get update -o Acquire::Retries=5 \
    && apt-get install -y --no-install-recommends openssl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /app/build ./build
COPY --from=build /app/package.json ./package.json
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/prisma ./prisma
COPY --from=build /app/CHANGELOG.md ./CHANGELOG.md

ENTRYPOINT ["node", "build"]
