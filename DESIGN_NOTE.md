# Design Note

> TODO before submitting: sections marked **[PERSONALIZE]** need to reflect
> what actually happened when *you* ran this, in your own words -- the rubric
> explicitly grades this on being "honest, specific, in your voice." Run the
> project first, hit a real error, then rewrite those bits.

## Architecture pattern

I used a **sequential pipeline** for ingestion (transcribe -> summarize into
structured JSON -> chunk and embed -> store) and a **router** for the one
place a real decision has to be made: what to do with each action item. The
ingestion stage has no branching, so making it agentic would only add
latency and unpredictability for no benefit. The action step does branch --
some action items need only a durable record, others also need a calendar
follow-up -- so I gave that step to an LLM agent instructed to route each
item to the right tool (`write_action_items` always, `create_calendar_event`
only when a due date is present), rather than hand-coding the branching logic
myself. The alternative I considered was a plan-and-execute agent for the
whole ingestion pipeline; I rejected it because the pipeline has a fixed
shape every time, and letting an LLM "plan" a sequence that never changes
just trades determinism for token spend.

## A failure I hit while building

I assumed the Anthropic Messages API still took a `temperature` kwarg like
every tutorial and the Session 1 material describe, and `messages.create(...,
temperature=0.2, ...)` raised `TypeError: Messages.create() got an unexpected
keyword argument 'temperature'`. The installed SDK matches the current Claude
5 model family, which dropped `temperature`/`top_p`/`top_k` entirely in favor
of an `output_config.effort` knob (`low`/`medium`/`high`/`xhigh`/`max`) plus,
separately, native JSON-schema-constrained output via `output_config.format`.
I confirmed this by sending a deliberately invalid API key and checking that
the error was a 401 from the server rather than a client-side shape error --
that told me the new request shape was correct, the key was just wrong. I
switched `src/llm.py` to build `output_config` instead of passing
`temperature`, and switched `src/summarizer.py` from prompt-only "output only
JSON" instructions to a real `json_schema` response format, which is strictly
better: malformed JSON is now rejected by the API itself instead of being
caught by my regex fallback after the fact.

**[PERSONALIZE]**: if you hit a *different* failure while running your own
recording through the pipeline (a whisper transcription quirk, a retrieval
miss, an agent iteration cap trip), swap this in instead -- the rubric wants
one real story, and yours from actually running it beats mine from building it.

## A tradeoff I made **[PERSONALIZE / verify against your run]**

I chose **low top-k (4) over a large one** for retrieval. With only 4-5
seeded meetings, a high k mostly pulls in irrelevant chunks and dilutes the
context the model is grounded in, which hurts citation accuracy more than it
helps recall. The cost is that a question spanning many meetings at once
might miss a relevant fact that didn't make the top 4. If you seed
significantly more meetings, raise `TOP_K` in `.env` and re-run `eval` to see
whether the tradeoff still holds -- report what you actually observed here.
