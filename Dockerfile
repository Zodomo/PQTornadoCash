FROM node:24.19.0-bookworm AS node

FROM rust:1.97.0-bookworm

ARG FOUNDRY_VERSION=v1.7.1
ARG PNPM_VERSION=11.20.0

COPY --from=node /usr/local /usr/local
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl git ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && npm install --global "pnpm@${PNPM_VERSION}" \
    && curl -fsSL https://foundry.paradigm.xyz | bash \
    && /root/.foundry/bin/foundryup --install "${FOUNDRY_VERSION}"

ENV PATH="/root/.foundry/bin:${PATH}"
WORKDIR /workspace
COPY . .
RUN cargo test --workspace --locked \
    && pnpm install --frozen-lockfile \
    && pnpm test \
    && forge build --sizes \
    && forge test
