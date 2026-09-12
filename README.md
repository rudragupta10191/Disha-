# Disha

Phase 1 foundation, Phase 2 first-run setup system, Phase 3 AI provider layer,
and Phase 4 private gateway for Disha, owned by
Rudra and intended to run in Termux on Android. Development is performed with
GitHub Copilot and Codespaces.

## Scope

This phase provides a modular Python package, environment-driven non-secret
configuration, logging, diagnostics, a CLI, and pytest coverage. The declared
primary AI is Cactus Needle 2. Disha detects it only when a real, readable
model and compatible runtime are available locally.

Hardware integrations and Telegram bots are intentionally outside these phases.
Cloud providers remain disabled unless explicitly configured, and the Phase 3
cloud configuration is reported as unverified because it performs no network
calls yet. Disha never downloads or creates a model. The Phase 4 gateway is
local-only, requires an explicit token, accepts registered commands only, and
does not execute shell commands. Phase 6 adds protocol-neutral Home IoT
registry and adapter contracts for a Haier AC and A9 camera. They perform no
discovery or network access and report `UNVERIFIED` until an explicit,
authorized protocol implementation is supplied. Device-changing commands are
accepted only through a registered handler and an authorization policy.

## Setup

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

Copy `.env.example` to `.env` only for local workflows. `.env` is ignored by
git. Do not place secrets in source files or commit them.

## CLI

```sh
disha
disha --diagnostics
disha --setup
```

The diagnostics command reports detected Termux/Android facts, provider status,
and Phase 1 integration status without printing environment secrets. Needle 2
reports `MISSING`, `UNAVAILABLE`, or `UNVERIFIED` when it cannot be confirmed.
Setup is optional and
can be skipped. It stores only local preferences in
`$XDG_CONFIG_HOME/disha/setup.json` or `~/.config/disha/setup.json`, with
owner-only permissions. No provider is downloaded or connected automatically.

## Private gateway

The gateway binds to `127.0.0.1` by default and rejects public bind addresses.
Requests use a bearer token from `DISHA_GATEWAY_TOKEN`, identify either
`Neo/Hermes` (master controller) or `Rudra` (owner), and are authorized against
server-side command risk levels `L0` through `L4`. Tokens and secret payload
fields are never written to security logs.

## Tests

```sh
pytest
```

This is an initial foundation and setup system, not a production-ready system.