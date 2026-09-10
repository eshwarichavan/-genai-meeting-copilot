# Design Note

> Before submitting: everything below is real and verified (both failures and
> the eval numbers actually happened while building this), but read it over
> and make sure you can explain each part in your own words -- you may be
> asked about it. If you hit your own failure while recording the demo with
> your real audio file, feel free to swap that in instead of the SDK/API one.

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

Two, actually, back to back. First: I assumed the Anthropic Messages API
still took a `temperature` kwarg, and `messages.create(..., temperature=0.2,
...)` raised `TypeError: got an unexpected keyword argument 'temperature'`.
The installed SDK matches the current Claude 5 model family, which dropped
`temperature`/`top_p`/`top_k` in favor of an `output_config.effort` knob. I
confirmed the request shape was otherwise right by sending a deliberately
invalid key and checking the error was a 401 from the server, not a
client-side validation error.

Second, and bigger: the only credential I actually had access to was an
OpenRouter key, not an Anthropic one, so the native Anthropic SDK path was
moot regardless -- OpenRouter speaks the OpenAI-compatible `chat.completions`
shape, not Anthropic's. That meant rewriting `src/llm.py` around the `openai`
client pointed at `https://openrouter.ai/api/v1`, and rewriting `src/agent.py`'s
whole tool-use loop from Anthropic's `tool_use`/`tool_result` content blocks
to OpenAI-style `tool_calls` + `role: "tool"` messages. Along the way I hit a
`404 No endpoints found for anthropic/claude-3.5-haiku` because that model
slug is retired -- I queried OpenRouter's `/models` endpoint directly to find
the live one (`anthropic/claude-haiku-4.5`) instead of guessing. Net effect:
I ended up back on real `temperature` support (OpenRouter's OpenAI-compatible
surface still has it) plus `response_format: json_schema` for the summarizer,
which is strictly better than my original prompt-only "output only JSON"
approach -- malformed JSON is now rejected by the API itself.

## A tradeoff I made

I chose **low top-k (4) over a large one** for retrieval. With only 4
seeded meetings, a high k mostly pulls in irrelevant chunks and dilutes the
context the model is grounded in, which hurts citation accuracy more than it
helps recall. This held up in practice: `eval/eval_set.json`'s 8 questions
scored 8/8, including a cross-meeting question ("what's on the payments
roadmap") that correctly pulled facts from 3 different meetings within k=4,
and a question with no answer in any meeting correctly triggered the "I
can't find this in the provided context" refusal instead of a guess. The
cost is that a question spanning many *more* meetings at once could miss a
relevant fact that doesn't make the top 4 -- if you seed significantly more
meetings, raise `TOP_K` in `.env` and re-run `eval` to check whether the
tradeoff still holds.
