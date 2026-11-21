<!-- source: _skills/persian-formal/SKILL.md -->

# Formal Persian (فارسی رسمی)

Formal Persian is the register models get most wrong: they write more
bureaucratic copy than a working Iranian writer would. Formal means full
written forms, «شما», no slang. It does not mean ceremony.

Default register for proposals: **رسمی روان** (formal-but-human). Use **اداری**
only for a letter to an organization, ministry, university, or bank.

## Register

| Register | Where | Marker |
|----------|--------|--------|
| Formal-but-human (رسمی روان) | Proposal, contract, invoice, terms, B2B email | است، شد، می‌شود؛ short sentences; concrete claims |
| Formal-administrative (اداری) | Letter to an organization | Same verbs plus letter furniture (موضوع، با سلام و احترام) |

## Verbs and vocabulary

- Use است، شد، کرد، می‌شود. Never می‌باشد، گردید، به عمل آورد، قرار دارد (for است)، محسوب می‌شود، به شمار می‌رود.
- Short sentences, one idea each. Do not chain clauses with که.
- Address the client as شما, not کاربران محترم.
- Prefer a natural Persian word when one exists: برای not جهت، درباره‌ی not در خصوص، به همین دلیل not از این رو.
- No fake tanvin on Persian words: گاهی not گاهاً، دوم اینکه not دوماً. Keep it on real Arabic loans: واقعاً، حتماً، لطفاً.

## Banned phrases

Cut on sight; say the thing instead.

| Tell | Replace with |
|------|----------------|
| لازم به ذکر است که / شایان ذکر است | (delete; state the fact) |
| در راستای / در همین راستا / در جهت نیل به | برای |
| از اهمیت ویژه‌ای برخوردار است / نقش بسزایی ایفا می‌کند | the concrete claim |
| در دنیای امروز / در عصر دیجیتال / امروزه با پیشرفت تکنولوژی | start with the point |
| در نهایت می‌توان گفت / به طور کلی | end with a fact or a next step |
| بی‌نظیر / منحصربه‌فرد / تجربه‌ای متفاوت | a number, a name, or nothing |
| سریع، آسان و مطمئن (any triad) | two items, or one developed idea |
| نه تنها … بلکه | the positive claim, plainly |
| — (em dash) | ، or a new sentence |

No همچنین opening three sentences in a row. No «امیدوارم مفید بوده باشد» closers.

## Proposal and commercial wording

Keep product names, APIs, and brand terms in their original Latin form. Do
not invent Academy coinages the client would not recognize. Prefer natural
business Persian over calques:

| English | Use |
|---------|-----|
| Proposal | پیشنهاد همکاری |
| Scope of work | محدوده کار |
| Deliverable | خروجی |
| Phase / milestone | مرحله |
| Timeline | زمان‌بندی |
| Investment / fee | مبلغ پروژه (not سرمایه‌گذاری unless it is equity) |
| Payment terms | شرایط پرداخت |
| Assumptions | مفروضات |
| Exclusions | خارج از محدوده |
| Recurring costs | هزینه‌های دوره‌ای |
| Next steps | گام‌های بعد |

Money: state the unit once («همه‌ی مبالغ به تومان است»). Never mix تومان and
ریال. Amounts that bind the parties also appear in words:
`۱۲٬۵۰۰٬۰۰۰ تومان (دوازده میلیون و پانصد هزار تومان)`.
Dates: Jalali `۲۹ شهریور ۱۴۰۵` or `۱۴۰۵/۰۶/۲۹`. Add Gregorian only if the
counterparty is outside Iran.

## Orthography

- ZWNJ (U+200C, نیم‌فاصله): می‌شود، شرکت‌ها، به‌عنوان، پیش‌فاکتور.
- Persian ی (U+06CC) and ک (U+06A9), never Arabic ي / ك.
- Persian digits ۰–۹ in prose; `٬` as thousands separator; `٪` after the number.
- گیومه «» for quotes; no space before ، ؛ .
- Do not write ezafe as ه («قراردادِ فروش» not «قرارداده فروش»).

After drafting, run the folder's `scripts/persian-normalize.py` on the
proposal file. That script only does Unicode-safe cleanup (NFC, ye/kaf,
digits, tatweel, duplicate ZWNJ, می/نمی prefix). It does not rewrite wording.
Wording still has to pass the checklist below.

Full mechanical cleanup (punctuation, more suffixes) is
[Virastar](https://github.com/brothersincode/virastar). Do not add it as a
project dependency; the normalize script covers the high-frequency errors.

## RTL document shape

Persian Markdown needs language and direction in the YAML frontmatter:

```yaml
---
lang: fa
dir: rtl
---
```

Optional PDF (only if the developer asks and `pandoc` plus XeLaTeX are
installed), with a Persian-capable font such as Vazirmatn:

```bash
pandoc PROPOSAL.md -o PROPOSAL.pdf --pdf-engine=xelatex -V mainfont="Vazirmatn" -V dir=rtl -V lang=fa
```

Do not apply `letter-spacing` on Persian HTML. Do not reverse letters by
hand; shaping belongs to the renderer.

## Checklist

1. Register is رسمی روان throughout (اداری only for an org letter).
2. Zero می‌باشد / گردید / لازم به ذکر است / در راستای.
3. No triads, no em dashes, no generic openers or closers.
4. Numbers, dates, and units are Persian and explicit; unit stated once.
5. Every commercial claim is in the PRD or the developer's approval.
6. `persian-normalize.py` has been run on the file.

## Sources

- [farsiui persian-formal](https://farsiui.ir/skills/persian-formal) — register, banned phrases, money/dates
- [Virastar](https://github.com/brothersincode/virastar) — ZWNJ, ye/kaf, digit cleanup
- [Pandoc `lang` / `dir`](https://pandoc.org/MANUAL.html) and XeLaTeX for RTL PDF
