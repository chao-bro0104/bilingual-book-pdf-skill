# Publication-Grade Literary Translation Guide

## 1. Translation Principles
- **Tone & Cadence**: Match the author/speaker's authentic voice—direct, candid, conversational, yet razor-sharp. Avoid stiff "translationese" (e.g., never translate *"Please interpret generously"* as *"请慷慨地解读"*; render as *"请以善意与宽容之心去理解与解读"*).
- **Punctuation & Spacing**:
  - Use standard Simplified Chinese punctuation (`“”`、`‘’`、`——`、`……`、`、`、`？`、`！`).
  - Insert a single space between Chinese characters and Latin words/digits (e.g., `SpaceX 火箭`, `Model 3 产线`, `100 小时`), except immediately adjacent to full-width Chinese punctuation.
- **Type-Specific Formatting**:
  - `chapter_title` / `section_title`: Concise, punchy Chinese titles with no trailing period.
  - `highlight`: Crisp, memorable aphorisms. If `en` is a JSON array (`list[str]`), `zh` **must** be a JSON array of the exact same length.
  - `question`: Must begin with `问：`.
  - `numbered`: Concise maxims without repeating the number (the renderer supplies the badge).
  - `timeline`: Keep consistent separator, e.g., `1984 年（12 岁）——开发了他的第一款电子游戏《Blast Star》。`.
  - `book_entry`: Use standard published Chinese book titles in guillemets followed by author (`《银河系漫游指南》——道格拉斯·亚当斯`).
  - `signoff`: Match array length to `en`.

## 2. Subagent Definition Template

Define a dedicated subagent (`define_subagent`) rather than `run_workflow(type_name="self")`:

- `Name`: `book_translator`
- `EnableWriteTools`: `True`
- `EnableMCPTools`: `False`
- `EnableSubagentTools`: `False`
- `SystemPrompt`: Include the rules above plus a **book-specific glossary** covering:
  - Book title & subtitle
  - Key people & recurring interviewers
  - Core concepts & idiosyncratic coinages (e.g., `first principles` → `第一性原理`)
  - Company, product, and proper-noun conventions (which stay in English vs. Chinese)

## 3. Parallel Wave Execution
1. Launch waves of **5–7** `invoke_subagent(TypeName="book_translator", Model="inherit", ...)` calls in parallel.
2. Each subagent prompt instructs it to:
   - Read `data/chunks/chunk_XX.json` via `read_file`
   - Write `{uid: zh, ...}` UTF-8 JSON to `data/translated/chunk_XX_zh.json` via `write_file(Overwrite=True)`
   - Run a short Python check via `run_command` verifying exact UID match and non-empty values
   - Reply `OK: chunk_XX`
3. End the turn after launching each wave and wait for reactive completion messages before launching the next wave.
4. Once all chunks report `OK`, run `scripts/validate_translations.py` across the whole book.
