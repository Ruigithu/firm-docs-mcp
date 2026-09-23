# Corpus

Test documents for development and evaluation.

**Public legal texts only.** No client material and no real personal data at any
point in this project. Evaluation cases are written against these documents, so
their answers are verifiable by anyone reading this repository.

Rebuild with `python corpus/build.py` (standard library only, no dependencies).

## Contents

| File | Instrument | Size | Relevance |
|---|---|---|---|
| `gdpr.txt` | Regulation (EU) 2016/679, Articles 1 to 99 | 188 KB | Data protection |
| `data-protection-act-2018.txt` | Data Protection Act 2018 (Ireland) | 440 KB | Data protection |
| `employment-equality-act-1998.txt` | Employment Equality Act 1998 | 213 KB | Employment |
| `residential-tenancies-act-2004.txt` | Residential Tenancies Act 2004 | 317 KB | Real estate |
| `unfair-dismissals-act-1977.txt` | Unfair Dismissals Act 1977 | 43 KB | Employment |

Roughly 1.2 million characters across five instruments.

## Why these

Four practice areas, deliberately. Retrieval accuracy only means something when
there is more than one plausible document to choose between, and the two
employment statutes overlap enough to be genuinely confusable. A single-document
corpus would make every retrieval case trivially passable.

The instruments are also substantively related without being duplicates: the
Data Protection Act 2018 gives effect to the GDPR in Irish law, so questions
exist whose answer lives in one and not the other.

## Sources

- Irish Acts: [Irish Statute Book](https://www.irishstatutebook.ie/), Office of
  the Attorney General. Retrieved from the `print` view of each Act.
- GDPR: retrieved article by article from [gdpr-info.eu](https://gdpr-info.eu/).
  This is a mirror, not the official source. EUR-Lex serves the official
  consolidated text but gates automated retrieval, so it cannot be fetched
  reproducibly. The article text matches the Official Journal; the provenance is
  stated here rather than glossed over.

## Two defects found while preparing this

Neither raised an error. Both are recorded here because a silent defect in the
corpus becomes a silent defect in the evaluation.

**Mixed encoding in a single document.** Irish Statute Book pages serve cp1252
site navigation wrapped around a UTF-8 Act body, while declaring UTF-8 in the
meta tag. Decoding the page as UTF-8 corrupts the navigation; decoding it as
cp1252 corrupts every accented character in the Act, turning `Coimisiún um
Chosaint Sonraí` into `CoimisiÃºn um Chosaint SonraÃ­`. The build slices the Act
container out of the raw bytes before decoding anything.

**Soft hyphens inside words.** The source text carries U+00AD at line-break
positions. The character is invisible when rendered, so the text looks correct,
but a substring search for `Sonraí` will not match `Sonra{U+00AD}í`. Since this
corpus is searched by substring, they are stripped at ingest.

## Preparing more documents

Add an entry to `IRISH_ACTS` in `build.py` and place the `print` view HTML in
`corpus/raw/`. Citation accuracy is scored against section and article numbers,
so the numbering must survive extraction.
