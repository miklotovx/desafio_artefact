# Empório da Música - Customer Service Agent

Python customer-service agent for the Artefact AI Engineer challenge. Implementation in progress.

## Technical decisions

| Decision | Choice and rationale |
| --- | --- |
| Agent approach | Function calling with Python tools and the Google SDK for simplicity and controlled queries. |
| Model and provider | Google Gemini 3.5 Flash-Lite through the Gemini API, a lightweight model for straightforward conversations. |
| Interface | Streamlit for a clean chat interface built in Python. |
| Conversation history | Streamlit `st.session_state` maintains context during the session. Separate Markdown logs preserve each conversation for evaluation. |
| Data treatment | Python's standard `csv` module loads the six tables into memory. Explicit types, `Decimal` for money, parsed JSON specifications and date conversion keep queries and calculations consistent. IDs and references are validated; optional empty fields become `None`. |
| Response handling | Keep the current conservative human-assistance fallback for this prototype. More specific handling of out-of-scope and unsupported requests is deferred to keep the implementation simple. |

`data_access.py` loads the supplied files from `data/`, independently of the working directory. Original CSVs and the policy PDF are preserved. The reviewed Markdown conversion provides the policy text without repeated page headers. Source contradictions are preserved rather than corrected through assumptions.

`tools.py` searches products, returns product details and prices, consults orders and retrieves complete policy sections by topic. This avoids a vector database for a small manual. Prices use active promotions or the 5% PIX discount, without stacking, rounded to cents. Multiple active promotions for one product produce an ambiguous price rather than an assumed discount. Order lookup requires the order number and matching email; this is a prototype check, not authentication. Recorded order totals are preserved.

Tracking has a dedicated query: an absent code returns the human-assistance offer. Responses containing a tracking code in the supplied BR format are checked against codes returned by order tools in the current request.

`agent.py` connects Gemini to these tools. Its instructions define the PT-BR persona, source consultation, handling of missing information and human assistance. Each message reloads the sources; tool exchanges preserve the SDK's original content. Requests are limited to 5 model rounds and 12 tool calls. API errors, invalid tool calls and unsuccessful lookups return the standard human-assistance offer.

## Scope and behavior

- **PT-BR only**, matching the Brazilian store and challenge examples.
- The catalog consists of the **65 supplied products**, despite the larger quantity mentioned in the manual.
- A registered category does not imply available products. Wind-instrument categories exist in the source, but no wind instruments are present in the supplied product catalog.
- The chat is always available.
- Queries cover products, prices, stock, orders, discounts, installments, returns, shipping and other store policies.
- Answers require explicit source information. Missing or contradictory information must not be filled in through assumptions. Calculations follow explicit rules.
- Product fields must retain their original spelling, including registration errors. Currency symbols are escaped for Streamlit display without changing session history.
- When unable to answer, the agent states that the request could not be processed and offers human assistance.
- The tone is friendly and professional, including when handling out-of-scope questions.

## Setup

Python 3.12. From the project folder, in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

No API key is supplied. Before testing, create `.env` from `.env.example` (or edit your existing `.env`) and manually insert your own Gemini API key:

```dotenv
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
```

Save the file and restart the application. The `.env` file is excluded from Git; `.env.example` contains no credentials. Without a key, the chat displays setup instructions and disables message input.

Start the chat:

On Windows, double-click `iniciar_chat.bat` to open the chat in your default browser. Keep the terminal open while using it; press Ctrl+C to stop.

Alternatively, use PowerShell:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address localhost
```

Open the local URL shown in the terminal. Use **Nova conversa** to clear the session history.

Conversation logging is part of the final application. Each new conversation creates a separate Markdown file in `logs/`, updated after each message. Previous logs are preserved when starting a new conversation. All recorded conversation logs will accompany the submission in this folder. Files retain the original customer and assistant text, including any personal information entered in the chat.

## Project structure

```text
app.py          # Streamlit interface and session history
agent.py        # Gemini integration and tool-call flow
tools.py        # Product, order and policy queries
data_access.py  # Source loading and validation
conversation_log.py # Local conversation recording
data/           # Supplied CSVs, original manual and Markdown conversion
logs/           # Recorded conversations included for evaluation
tests/          # Agent and chat checks without live API calls
```

## Validation and limitations

The candidate exercised the 30-case manual checklist, covering store information, policies, products, prices, orders, history and response boundaries. Some scenarios returned the human-assistance offer instead of the more specific expected explanation, including an unavailable product and out-of-scope requests. These behaviors are retained as prototype limitations. The missing-tracking issue was corrected and retested.

Four recorded conversations in `logs/` demonstrate catalog filtering and active discounts, available instrument types and the absence of wind instruments, price comparisons and shipping/return policies, and order tracking after requesting the order number and email. These cover the required 3-5 examples, including non-trivial data and policy queries. All recorded logs will be submitted.

Data loading was checked against all six CSVs and the policy manual, including invalid values, duplicate IDs, broken references, missing files and an empty manual. Tool checks covered available products under a price ceiling, discounts and PIX non-stacking, unavailable products, order-email matching, historical totals, complete policy sections and ambiguous promotions.

Automated tests use simulated API responses to check tool exchanges, history, invalid arguments, call limits and failures. Streamlit tests cover missing configuration, message history and conversation reset:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Live Gemini queries were tested. Technical failures are logged in the terminal by exception type and HTTP status, without exception details or customer content. Model instructions do not guarantee factual compliance beyond the cases tested.

The agent's context is session-only; local conversation logs persist separately and are not reloaded as context. Human assistance is offered but not connected to a live attendant. The agent provides guidance; purchases, cancellations and returns are not executed.

Manual testing also exposed an internal CSV field name in a response. Explicit requests for CSV information were redirected to human assistance in the candidate's additional tests, but this does not establish comprehensive protection against source or schema disclosure. The candidate chose to retain the current behavior for this prototype. With more time, responses would receive stronger output validation to hide internal field names and more specific handling of unsupported requests.

## AI assistance

Codex assists with planning and development under the candidate's direction. The accompanying redacted conversation log documents the workflow.

The initial local commits were created after implementation, grouped by component. They do not represent the original development timeline; the conversation log records that process.

## Development checklist

- [x] Implement and validate source loading and data treatment; document the rationale.
- [x] Implement and check product, order and policy tools.
- [x] Implement the agent and verify its tool-call flow with simulated responses.
- [x] Validate the agent with the live Gemini API and document observed limitations.
- [x] Implement the Streamlit chat, including session history.
- [x] Add application startup instructions and project structure.
- [x] Run manual checks and document deviations from expected behavior.
- [x] Record 3-5 example conversations, including non-trivial scenarios, in `logs/`.
- [x] Document known limitations and improvements that would be made with more time.
- [x] Configure the GitHub noreply author email.
- [x] Record local commits grouped by component.
- [ ] Update the redacted conversation log before delivery.
- [ ] Publish the repository with its commit history and make no changes after submission.
- [ ] Review the final README against the challenge requirements and remove this development checklist.
