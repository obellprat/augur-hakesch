FROM node:23-alpine AS build

ARG DATABASE_URL=${DATABASE_URL}

ENV DATABASE_URL=${DATABASE_URL}

WORKDIR /app

COPY . .

RUN npm ci

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
