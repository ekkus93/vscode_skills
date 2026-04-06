# Skill List

This file lists reusable skills available in the shared workspace skill library.

## How to use this index
1. Match the user task to the closest skill.
2. Open that skill directory.
3. Read the skill's `SKILL.md`.
4. Follow the skill's procedure, constraints, and output format.
5. Do not claim to have used a skill unless you actually read its `SKILL.md`.

## Skills

### stock-investment-review
- Path: `skills/stock-investment-review/`
- Use for: producing a saved stock investment review with a TODO file and Markdown report for a public ticker over a default 30-day horizon or another explicit short-term range
- Typical outputs: `<TICKER>_TODO.md`, `<TICKER>.md`, scenario-based stock review, action/entry/exit/invalidation sections

### stock-research
- Path: `skills/stock-research/`
- Use for: building a longer-form public stock research snapshot that combines market data, company context, and recent headlines
- Typical outputs: stock research summary, market snapshot, business profile, recent market news, recent company news

### company-research
- Path: `skills/company-research/`
- Use for: researching a company from official-site context first, then adding recent company news as supporting context
- Typical outputs: company summary, docs/pricing/careers signals, official URLs, recent company news

### news-search
- Path: `skills/news-search/`
- Use for: finding recent distinct news stories for a topic with source names, dates, links, and deduplicated coverage
- Typical outputs: recent coverage summary, distinct story list, paywall note, source-linked headlines

### yahoo-finance
- Path: `skills/yahoo-finance/`
- Use for: fetching a concise market snapshot for one public stock or ETF ticker with recent performance and basic fundamentals
- Typical outputs: price snapshot, sampled performance, valuation metrics, fundamentals summary

### stock-review-market-context
- Path: `skills/stock-review-market-context/`
- Use for: internal companion rules for one-year market context, technical levels, and bundled stock-review helper usage
- Typical outputs: one-year price context, technical posture summary, helper invocation guidance

### stock-review-output-contract
- Path: `skills/stock-review-output-contract/`
- Use for: internal companion rules for required TODO/report files and the exact final decision section layout
- Typical outputs: TODO structure requirements, report section contract, final decision template

### stock-review-supporting-research
- Path: `skills/stock-review-supporting-research/`
- Use for: internal companion rules for official-site context, recent catalysts, and bundled helper invocation guidance
- Typical outputs: supporting research workflow, company/news helper guidance, corroborating-source rules

### arxiv-search
- Path: `skills/arxiv-search/`
- Use for: searching arXiv for papers by topic, author, category, title, or abstract query
- Typical outputs: concise paper shortlist, abstract links, PDF links, short metadata summaries

### audio-transcribe
- Path: `skills/audio-transcribe/`
- Use for: transcribing a local audio or video file fully offline into a clean plain-text workspace artifact
- Typical outputs: `outputs/transcripts/<original-file-prefix>_transcript.txt`, saved transcript path confirmation

### yahoo-finance-cli
- Path: `skills/yahoo-finance-cli/`
- Use for: fetching stock prices, financial data, and market summaries using Yahoo Finance CLI
- Typical outputs: stock quotes, financial metrics, market overviews

### current-date-time
- Path: `skills/current-date-time/`
- Use for: getting the current local date, current time, or current datetime from the system clock
- Typical outputs: current local time, current date, UTC timestamp

### weather
- Path: `skills/weather/`
- Use for: getting the current weather, temperature, and simple forecast for a city or location
- Typical outputs: current conditions, temperature summary, short forecast

### wikipedia
- Path: `skills/wikipedia/`
- Use for: searching Wikipedia and getting a concise summary for a topic, person, place, event, or concept
- Typical outputs: page summary, resolved topic title, short encyclopedia overview

### docx-to-markdown
- Path: `skills/docx-to-markdown/`
- Use for: converting `.docx` and legacy `.doc` files into Markdown `.md` files
- Typical outputs: converted markdown file, output path confirmation

### excel-to-markdown
- Path: `skills/excel-to-markdown/`
- Use for: converting local `.xlsx` and `.xls` workbooks into a single Markdown file for readable workbook review
- Typical outputs: converted markdown workbook, output path confirmation, per-sheet markdown sections

### excel-to-delimited
- Path: `skills/excel-to-delimited/`
- Use for: converting local `.xlsx` and `.xls` workbooks into per-sheet `.csv` or `.tsv` exports
- Typical outputs: output directory path, per-sheet delimited files, sheet-oriented machine-friendly exports

### image-ocr
- Path: `skills/image-ocr/`
- Use for: extracting text from image files with OCR using Tesseract
- Typical outputs: OCR text file, extracted text preview, output path confirmation

### bitcoin-price
- Path: `skills/bitcoin-price/`
- Use for: getting the current Bitcoin price in USD
- Typical outputs: current BTC price, short Bitcoin price summary

### hacker-news-top10
- Path: `skills/hacker-news-top10/`
- Use for: getting the current top 10 Hacker News stories with titles, URLs, and short summaries
- Typical outputs: top 10 story list, article links, short story summaries

### net-diagnose-incident
- Path: `skills/net-diagnose-incident/`
- Use for: orchestrating a full NETTOOLS incident investigation across the lower-level network skills from complaint intake through ranked diagnosis
- Typical outputs: diagnosis report, incident state, audit trail, investigation metrics, replayable investigation artifacts

### net-incident-intake
- Path: `skills/net-incident-intake/`
- Use for: normalizing a freeform complaint into a structured NETTOOLS incident record with follow-up skill hints
- Typical outputs: incident record, extracted scope hints, recommended next-step skills

### net-client-health
- Path: `skills/net-client-health/`
- Use for: assessing one Wi-Fi client session for RF quality, retries, reconnects, and roam symptoms
- Typical outputs: client RF findings, retry and loss evidence, connected AP context, follow-up skill recommendations

### net-ap-rf-health
- Path: `skills/net-ap-rf-health/`
- Use for: evaluating AP radio conditions, utilization, load, resets, and RF instability indicators
- Typical outputs: AP RF findings, utilization and client-load evidence, neighboring AP context

### net-dhcp-path
- Path: `skills/net-dhcp-path/`
- Use for: checking DHCP latency, timeouts, relay behavior, and address-allocation symptoms for a client, SSID, VLAN, or site scope
- Typical outputs: DHCP path findings, offer and ACK latency evidence, scope-utilization context, follow-up recommendations

### net-dns-latency
- Path: `skills/net-dns-latency/`
- Use for: measuring internal DNS latency, timeout rate, and resolver quality for a client, SSID, or site scope
- Typical outputs: DNS findings, resolver latency evidence, timeout-rate evidence, follow-up recommendations

### net-roaming-analysis
- Path: `skills/net-roaming-analysis/`
- Use for: analyzing Wi-Fi roaming behavior, failed roams, latency, and sticky-client symptoms for one client
- Typical outputs: roam-history findings, failed-roam evidence, latency summaries, AP-transition context

### net-auth-8021x-radius
- Path: `skills/net-auth-8021x-radius/`
- Use for: evaluating 802.1X and RADIUS delays, timeouts, reachability, and repeated authentication failures
- Typical outputs: auth findings, success-rate and timeout evidence, RADIUS reachability metrics, follow-up recommendations

### net-path-probe
- Path: `skills/net-path-probe/`
- Use for: probing internal paths to compare latency, jitter, and loss across key service or gateway targets
- Typical outputs: degraded-target findings, per-target path evidence, service or site-wide path classification

### net-segmentation-policy
- Path: `skills/net-segmentation-policy/`
- Use for: verifying VLAN, DHCP-scope, gateway, and policy alignment for a client against expected segmentation
- Typical outputs: policy-placement findings, observed versus expected VLAN evidence, follow-up recommendations

### net-ap-uplink-health
- Path: `skills/net-ap-uplink-health/`
- Use for: validating the switch-port, uplink speed, errors, flaps, and PoE state behind an access point
- Typical outputs: uplink findings, switch-port evidence, PoE and configuration mismatch context

### net-stp-loop-anomaly
- Path: `skills/net-stp-loop-anomaly/`
- Use for: detecting topology churn, root changes, MAC flaps, and switching-loop symptoms that can cause widespread slowness
- Typical outputs: L2 instability findings, topology-change evidence, suspect-port context

### net-incident-correlation
- Path: `skills/net-incident-correlation/`
- Use for: correlating incident timing with network events, anomalies, and recent change windows
- Typical outputs: correlated-event evidence, ranked anomaly context, suggested follow-up skills

### net-change-detection
- Path: `skills/net-change-detection/`
- Use for: identifying recent infrastructure or configuration changes that align with a complaint window
- Typical outputs: ranked recent changes, change-correlation findings, likely review or rollback targets

### net-capture-trigger
- Path: `skills/net-capture-trigger/`
- Use for: preparing a gated packet-capture plan when telemetry suggests a narrow protocol failure and authorization permits it
- Typical outputs: manual capture plan, derived filter hints, authorization state, narrowed next steps