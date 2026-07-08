# hermes-omw

**Cited recall for [Hermes Agent](https://github.com/NousResearch/Hermes-Agent)** — a
bridge plugin that connects your [oh-my-wiki](https://github.com/dandacompany/oh-my-wiki)
knowledge vault to Hermes.

한국어 문서: [README.ko.md](./README.ko.md)

Most memory plugins auto-save conversation snippets into a black box you can't audit.
hermes-omw takes the opposite position: it exposes a **human-curated wiki** as tools, so
Hermes answers from pages you actually reviewed — **with citations** back to the source
pages. It is a plain tool plugin (not a memory provider), so it coexists with whatever
memory system you already run.

Concretely, it wires three tools and one slash command into Hermes via `plugin.yaml` +
`register(ctx)`, and routes every call through a single stdlib-only subprocess wrapper
around the `omw` CLI.

## Tools

| Tool          | What it does                                                                               | Wraps             |
| ------------- | ------------------------------------------------------------------------------------------ | ----------------- |
| `omw_find`    | Ranked wiki search — title, summary, tags, score. For quick lookups and page discovery.    | `omw find --json` |
| `omw_context` | Page bodies **plus a citations manifest** — for answering questions grounded in the wiki.  | `omw context`     |
| `omw_ingest`  | Fetch a public URL into the wiki's `raw/` layer and reindex. URL only, never writes pages. | `omw fetch`       |
| `/omw-status` | In-session slash command — active vault summary and available tools.                       | `omw status`      |

All tools accept an optional `vault` parameter (defaults to the active vault); the read
tools also accept `limit` (clamped to 1–50).

## Requirements

- [oh-my-wiki](https://github.com/dandacompany/oh-my-wiki) CLI: `pipx install oh-my-wiki`
- An active wiki-mode vault:

```bash
omw vault create my-wiki --mode wiki
omw vault use my-wiki
```

If the `omw` binary is not on Hermes' `PATH`, point to it with the `OMW_BIN` environment
variable.

## Install

Hermes plugins are directories dropped under `~/.hermes/plugins/`, each with a
`plugin.yaml` manifest and an `__init__.py` exposing `register(ctx)` — this repo already
has that shape at its root.

### Option A — clone + symlink (recommended for development)

```bash
git clone https://github.com/dandacompany/hermes-omw.git ~/src/hermes-omw
mkdir -p ~/.hermes/plugins
ln -s ~/src/hermes-omw ~/.hermes/plugins/omw
```

A plain copy (`cp -r` instead of `ln -s`) works identically; the symlink just makes
`git pull` in the source checkout update the plugin in place.

### Option B — `hermes plugins install`

```bash
hermes plugins install dandacompany/hermes-omw
```

This accepts `owner/repo` shorthand or a full git URL and clones the repo into
`~/.hermes/plugins/`. It asks `Enable 'omw' now? [y/N]` — answer `y`, or pass
`--enable` / `--no-enable` to skip the prompt in a scripted install.

### Verify

```bash
hermes plugins list          # expect: omw, version 0.1.0, not enabled (opt-in by default)
hermes plugins enable omw
```

Enabling prompts `Allow this plugin to replace built-in tools? [y/N]` — answer **no**.
hermes-omw only registers three tools and one command; it overrides nothing. Restart your
session (or `/reset`, or `hermes gateway restart`), then confirm the connection:

```
/omw-status
```

> Why `/omw-status` and not `/omw`? If you also installed oh-my-wiki as a Hermes **skill**,
> `/omw` collides with the skill loader — the command name stays out of its way.

## Usage

Just talk to Hermes:

- _"Search my wiki for attention mechanisms"_ → `omw_find`
- _"What does my wiki say about X? Cite the pages."_ → `omw_context` — the answer quotes
  hit bodies and cites the returned pages
- _"Save this link into my wiki: https://…"_ → `omw_ingest` — lands in `raw/`, ready for
  later distillation into wiki pages

## Design notes

- **Single access path.** Every tool call goes through `omw_client.run_omw()` — a
  stdlib-only subprocess wrapper that never raises. Missing binary, timeouts, non-zero
  exits, and non-JSON output all come back as structured error JSON with hints.
- **Deterministic writes only.** `omw_ingest` wraps `omw fetch` (deterministic:
  URL → `raw/` → reindex). Free-text ingestion needs LLM judgment, so it deliberately
  stays out of the tool surface — that's your agent's job, in conversation.
- **No Hermes internals.** The plugin imports nothing from Hermes and has zero runtime
  dependencies beyond the Python standard library, so the tests run anywhere.

## Security

`omw_ingest` is the only tool that performs network egress, and its argument (a URL)
comes from the LLM. To limit SSRF, the plugin validates the URL **before** delegating to
`omw fetch`:

- Only `http`/`https` schemes are accepted (case-insensitive).
- Non-canonical numeric IP literals (integer `2130706433`, octal `0177.0.0.1`, hex
  `0x7f.0.0.1`) are rejected outright.
- The hostname is DNS-resolved and requests to loopback, private, link-local, reserved,
  multicast, or unspecified addresses — including the cloud metadata endpoint
  `169.254.169.254` — are blocked.

**Known limitation (best-effort):** the actual fetch is delegated to the external
`omw fetch` CLI, which resolves the hostname a second time, so this boundary cannot fully
prevent **DNS-rebinding (TOCTOU)**. Closing it completely would require pinning the
resolved IP into the connection — only possible by performing the fetch inside the plugin,
contrary to the thin-wrapper design. The realistic attack surface (literal and
resolve-time private targets) is blocked; the rebinding residual is a documented, accepted
limitation.

## Layout

The standard Hermes 4-file plugin (`plugin.yaml`, `__init__.py`, `schemas.py`, `tools.py`)
plus `omw_client.py`, the single subprocess wrapper. No runtime dependencies beyond the
Python standard library. From a source checkout, the test suite runs without an omw
installation (the subprocess boundary is mocked):

```bash
python3 -m pytest tests/ -v
```

## License

[MIT](./LICENSE) © Dante Labs

---

**Dante Labs** · **YouTube** [@dante-labs](https://youtube.com/@dante-labs) · **Email** [dante@dante-labs.com](mailto:dante@dante-labs.com) · **Discord** [Dante Labs Community](https://discord.com/invite/rXyy5e9ujs) · **Support** [Buy Me a Coffee](https://buymeacoffee.com/dante.labs)
