# Roadmap

An MCP server, written in Rust, that lets an LLM client search and read a
document library over Microsoft Graph, with every answer traceable to a source
and every access recorded.

The design constraint that drives everything below: this component sits between
a language model and confidential documents. It must be able to show what the
model asked for, what it was given, and what it was refused.

---

## Milestones

Each milestone is independently demonstrable. The project is useful from M1
onward; M2 and M3 are what make it defensible.

### M0: Environment

- [x] Rust toolchain installed and verified
- [x] `uv` installed and verified
- [x] Repository initialised, `.gitignore` covering build output and secrets
- [x] Test corpus assembled (public legal texts only)

### M1: Working MCP server over local files

- [ ] `DocumentSource` trait: `search` and `read`
- [ ] `LocalFs` implementation reading from `corpus/`
- [ ] Tool `search_documents(query, limit)`
- [ ] Tool `read_document(id, max_chars)`
- [ ] Tool descriptions written as prompts, not as API docs
- [ ] `readOnlyHint` annotations set
- [ ] Registered with an MCP client and answering questions

**Done when:** asking "how long do we have to notify the supervisory authority
of a personal data breach?" returns 72 hours, citing GDPR Article 33, with the
source file named.

### M2: Microsoft Graph as a data source

- [ ] Entra ID app registration, delegated `Files.Read` and `offline_access`
- [ ] OAuth 2.0 authorization code flow with PKCE
- [ ] Local callback listener for the authorization code
- [ ] Token cache with automatic refresh
- [ ] `GraphApi` implementation of `DocumentSource`
- [ ] 429 handling: honour `Retry-After`, exponential backoff with jitter,
      bounded retries
- [ ] Pagination via `@odata.nextLink`
- [ ] Error mapping: "not found" and "not permitted" must reach the model as
      distinct messages

**Done when:** the M1 question returns the same answer with the data source
switched to Graph, changing configuration only.

**Scope note:** delegated permissions mean the server can only ever see what the
signed-in user can see. Access control is inherited from the document store
rather than reimplemented here. This is deliberate: in a professional services
setting, existing permissions already encode information barriers, and
reimplementing them is risk without benefit.

### M3: Context budget, audit, and tests

- [ ] Chunking and relevance ordering
- [ ] Response fits a stated character budget
- [ ] Truncation is declared explicitly in the returned content
- [ ] Structured audit log: timestamp, principal, tool, parameters, outcome,
      bytes returned, truncation flag, duration
- [ ] Refused calls are logged with a reason, not silently dropped
- [ ] `MockSource` implementation
- [ ] Unit tests covering tools, parameter validation, and retry logic, with no
      network access

**Done when:** `cargo test` passes offline and the audit log accounts for every
call made during a session, including the ones that were refused.

### M4: Evaluation

- [ ] Python evaluation harness managed with `uv`
- [ ] 20–25 cases across four categories:
  - retrieval accuracy (does it find the right document)
  - citation correctness (does the cited passage support the claim)
  - refusal (does it decline when the corpus has no answer)
  - authorization (are out-of-scope requests refused and logged)
- [ ] Scoring script recording answer, tool calls, and citations per case
- [ ] Results table in the README, including failures

**Done when:** the README carries real numbers, and every failing case has a
stated cause.

### M5: Delivery

- [ ] CI: `cargo fmt --check`, `cargo clippy -D warnings`, `cargo test`,
      `uv run pytest`
- [ ] README written for two audiences: what it solves, then how it works
- [ ] Architecture diagram
- [ ] Short demo recording
- [ ] Known limitations, stated plainly

---

## Standing practices

- Feature branches and pull requests, with written descriptions, including for
  solo work.
- No credentials, tokens, or client data in the repository or its history.
- Public legal texts only. No real client material at any point.

---

## Out of scope

- **A user interface.** The MCP client provides it. Building another would
  duplicate the client.
- **Content-level PII redaction as a security control.** Regex redaction has a
  high miss rate, and in a legal context redaction frequently destroys the
  usefulness of the answer. Data protection at this layer belongs to sensitivity
  labels and tenant DLP policy. This server's contribution is least privilege
  and an audit trail.
- **Legal judgement.** The tools retrieve and cite. They do not advise, and the
  tool descriptions say so.

---

## Possible extensions

- `get_matter_activity`: recent file changes and calendar events for a given
  matter, using delta queries.
- A Power Automate flow invoking the service, to show where this sits in a
  Microsoft 365 estate.
