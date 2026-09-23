# Corpus

Test documents for development and evaluation.

**Public legal texts only.** No client material, no real personal data, at any
point in this project. The evaluation cases are written against these documents,
so their answers are verifiable by anyone reading this repository.

Large binaries are not committed (see `.gitignore`). Plain-text extracts are.

## Sources

| File | Source |
|---|---|
| `gdpr.txt` | Regulation (EU) 2016/679, consolidated text, EUR-Lex |
| `dpa2018.txt` | Data Protection Act 2018 (Ireland), Irish Statute Book |

Both are published by their respective public bodies and are reproducible from
the links above.

## Why these two

They are the substantive law behind a commercial firm's data protection
practice, they overlap without being identical, and questions about them have
checkable answers. That last property is what makes them usable as an
evaluation corpus rather than just as demo filler.

## Preparing the text

Extract to UTF-8 plain text, one file per instrument, preserving article and
section numbering. Citation accuracy is scored against those numbers, so the
structure matters more than the formatting.
