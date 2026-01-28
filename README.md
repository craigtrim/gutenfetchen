# gutenfetchen

[![PyPI version](https://img.shields.io/pypi/v/gutenfetchen.svg)](https://pypi.org/project/gutenfetchen/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI Downloads](https://static.pepy.tech/badge/gutenfetchen)](https://pepy.tech/projects/gutenfetchen)
[![PyPI Downloads/Month](https://static.pepy.tech/badge/gutenfetchen/month)](https://pepy.tech/projects/gutenfetchen)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](https://mypy-lang.org/)

*Verb, pseudo-German.* **gutenfetchen** (/ˈɡuːtənˌfɛtʃən/) "to do the good fetching." From *guten* (good) + *fetchen* (to fetch), conjugated in the infinitive as if it were a proper German verb. Because downloading public-domain literature should feel orderly, efficient, and vaguely Teutonic.

Download plain-text e-books from [Project Gutenberg](https://www.gutenberg.org/) with a single command.


## Why gutenfetchen?

Most Gutenberg tools ([Gutenberg](https://pypi.org/project/Gutenberg/), [gutenbergpy](https://pypi.org/project/gutenbergpy/)) require building a local metadata database before you can do anything - a process that can take **hours**. gutenfetchen skips all of that.

- **Zero setup** - queries the [Gutendex API](https://gutendex.com/) directly, no local database required
- **Smart deduplication** - filters out duplicate editions, keeps the highest-quality version
- **Clean output** - strips Project Gutenberg boilerplate headers/footers by default
- **Prefers UTF-8** - automatically selects the best plain-text encoding available
- **Dry-run mode** - preview results before downloading anything

## Install

```bash
pip install gutenfetchen
```

## Usage

**Search by title:**

```bash
gutenfetchen "tale of two cities"
```

**Search by author:**

```bash
gutenfetchen --author "joseph conrad"
```

**Combine author + title filter:**

```bash
gutenfetchen "heart" --author "joseph conrad"
```

**Download random e-texts:**

```bash
gutenfetchen --random 5
```

**Preview without downloading:**

```bash
gutenfetchen --author "jane austen" --dry-run
```

**Limit results and set output directory:**

```bash
gutenfetchen --author "mark twain" --n 3 -o ./my_texts/
```

**Keep Gutenberg boilerplate (skip cleaning):**

```bash
gutenfetchen "moby dick" --no-clean
```

## Options

```
positional:
  title                  Search by title (e.g., 'tale of two cities')

options:
  --author NAME          Search by author name (e.g., 'joseph conrad')
  --random N             Download N random e-texts
  --n N                  Maximum number of texts to download
  -o, --output-dir DIR   Output directory (default: ./gutenberg_texts/)
  --dry-run              List matching books without downloading
  --no-clean             Skip stripping Project Gutenberg boilerplate
```
