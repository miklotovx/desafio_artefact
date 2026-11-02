# Empório da Música - Customer Service Agent

Python customer-service prototype for the Artefact AI Engineer challenge.

## Technical decisions

| Decision | Choice and rationale |
| --- | --- |
| Agent approach | Function calling with Python tools and the Google SDK for simplicity and controlled queries, without an agent framework. |
| Model and provider | Google Gemini 3.5 Flash-Lite through the Gemini API, a lightweight model for straightforward conversations. |
| Interface | Streamlit provides a clean chat interface in Python, used instead of the WhatsApp channel described in the manual. |
| Conversation history | `st.session_state` maintains session context. Separate Markdown files preserve conversations for evaluation. |
| Data treatment | Six CSVs are loaded in memory using `csv`, with explicit types, `Decimal` for money, parsed JSON specifications, validated IDs/references and `None` for optional empty fields. Complete policy sections are retrieved from the reviewed Markdown conversion, avoiding a vector database for a small manual. |

## Scope

- PT-BR customer interaction, matching the Brazilian store and challenge examples; chat always available.
- Only the 65 supplied products constitute the catalog. Registered categories do not imply available products: wind-instrument categories have no products in this dataset.
- Queries cover products, stock, prices, promotions, orders and store policies.
- Instructions require explicit source facts and preservation of product spelling, including registration errors. Missing or contradictory information leads to an offer of human assistance.
- Python calculates prices, applying active promotions or the 5% PIX discount without stacking. Original order totals are preserved. Tracking codes are checked against current order-tool results.

## Setup and execution

Use Python 3.12. In PowerShell, from this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

No API key is supplied. Manually insert your own key in `.env`:

```dotenv
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
```

Internet access is required. Keep `.env` private; it is excluded from Git. If it already exists, edit it directly. Without a key, message input is disabled.

Double-click `iniciar_chat.bat` on Windows, or run:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address localhost
```

Open the displayed local URL. Keep the terminal open; press Ctrl+C to stop. Restart after changing configuration.

## Structure and conversation logs

```text
app.py               # Chat interface and session history
agent.py             # Gemini integration and tool-call flow
tools.py             # Product, order, tracking and policy queries
data_access.py       # Source loading and validation
conversation_log.py  # Local conversation recording
iniciar_chat.bat     # Windows launcher
data/                # Supplied CSVs, original PDF and Markdown manual
logs/                # Recorded conversations for evaluation
tests/               # Automated checks and manual_test.txt
log_LLM.txt          # Redacted human/LLM development conversation
```

The `logs/` folder contains **four Markdown files with conversations used to evaluate the agent**, fulfilling the challenge requirement for 3-5 example conversations. They cover catalog queries, promotions, product availability, shipping and return policies, and order tracking, including non-trivial scenarios.

Each session creates a Markdown file in `logs/`, updated after every message. **Nova conversa** clears context and creates a new file without deleting previous logs. Logging remains part of the final application. Files preserve entered text, including any personal information, and are not reloaded as context.

## Validation

The candidate exercised a 30-case manual checklist. Inside the folder tests, the manual_test.txt lists the executed tests, expected behavior and reported results, including deviations and the tracking-code retest. Four recorded conversations demonstrate catalog queries, active discounts, categories without products, shipping/return policies and order tracking, including non-trivial data and policy scenarios.

Sixteen automated tests cover tool exchanges, invalid arguments, call limits, failures, tracking-code validation, chat history and log preservation, using simulated API responses:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Limitations and improvements

- Some unavailable-product, out-of-scope and unsupported requests receive a generic human-assistance offer instead of a specific explanation. This conservative behavior is retained for simplicity.
- Manual testing exposed an internal CSV field name. Requests for CSV information were redirected in additional tests, but comprehensive protection against source/schema disclosure is not established. This limitation is retained for the prototype.
- Order number/email matching is a prototype ownership check, not authentication. There is no live tracking integration, human transfer or execution of purchases, cancellations or returns.
- API latency and availability vary. Model instructions do not guarantee factual compliance beyond tested cases.

With more time, output validation would be strengthened to hide internal fields and verify source fidelity, alongside more specific handling of unsupported requests and broader regression coverage.

## AI assistance

Codex assisted with planning, source inspection, implementation and debugging under the candidate's direction. The full human/LLM conversation is available in log_LLM.txt, with sensitive information redacted. It documents this workflow and is updated through the latest export. Initial commits were created after implementation, grouped by component; they do not represent the original development timeline.
