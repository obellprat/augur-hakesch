FROM node:23-alpine AS build

WORKDIR /app

COPY package*.json .

RUN npm ci

COPY . .
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