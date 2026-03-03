FROM node:23-alpine AS build

ARG DATABASE_URL=${DATABASE_URL}

ENV DATABASE_URL=${DATABASE_URL}

WORKDIR /app

COPY CHANGELOG.md /CHANGELOG.md
COPY src/frontend/package.json ./package.json
COPY src/frontend/package-lock.json ./package-lock.json
COPY src/frontend/scripts ./scripts
COPY src/frontend/prisma ./prisma

RUN apk update
RUN apk add git

RUN npm ci

COPY src/frontend .

RUN npx prisma generate
RUN npm run build

FROM node:23-alpine AS run

ENV NODE_ENV=production

WORKDIR /app
COPY --from=build /app/build ./build
COPY --from=build /app/package.json ./package.json
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/prisma ./prisma

ENTRYPOINT ["node", "build"]
