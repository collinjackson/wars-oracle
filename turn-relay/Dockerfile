FROM node:20-slim

WORKDIR /app

COPY package.json tsconfig.json ./
RUN npm install

COPY api ./api

RUN npm run build

ENV NODE_ENV=production

CMD ["node", "dist/api/turn-relay.js"]

