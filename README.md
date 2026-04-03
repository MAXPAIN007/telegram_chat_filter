# Telegram Chat Filter

Telegram Chat Filter is a local web tool for processing Telegram export JSON files.

It is designed to help users:
- upload raw Telegram JSON exports;
- filter chats using either a simple or advanced filtering flow;
- remove unnecessary technical fields from messages;
- build clean, structured JSON files for manual analysis or AI processing;
- generate full snapshots and delta-based outputs;
- optionally send prepared files to an external agent or automation workflow through a webhook.

The application runs locally on the user's machine through a browser UI and a local Flask server.

No Telegram data is sent anywhere automatically.  
External sending only happens manually through the **Send to agent** button, if a webhook is configured.

---

## What this project is for

Telegram exports usually contain a lot of raw technical data that is inconvenient for analysis.

This project turns those exports into cleaner, more useful outputs by providing:

1. **Basic filtering** for quick keyword-based processing.
2. **Advanced filtering** with a visual filter builder.
3. **Message cleanup** that keeps only the useful fields.
4. **Full combined outputs** for the current run.
5. **Delta outputs** for changes between runs.
6. **Optional webhook delivery** to external agents such as n8n, Windmill, or custom workflows.

---

## Main features

- local Flask-based web interface
- upload one or multiple Telegram export JSON files
- **Basic mode**
- **Advanced mode**
- visual **Filter Builder**
- include / exclude filter rules
- date range filtering
- output mode selection:
  - full matching chats
  - matched messages only
- full combined output file
- delta update files
- isolated delta history for each advanced filter profile
- optional webhook sending to an external agent
- Russian / English UI

---

## Processing modes

## Basic mode

Basic mode is the simple workflow.

It allows you to:
- choose a global filter mode:
  - `Include`
  - `Exclude`
- enter keywords
- process uploaded Telegram JSON files quickly

This mode is useful for fast, repeatable filtering.

---

## Advanced mode

Advanced mode is intended for more flexible and reusable filtering.

It includes:
- `Match mode`
  - `ALL filters must match`
  - `ANY filter may match`
- `Output mode`
  - `Full matching chats`
  - `Matched messages only`
- `Date from`
- `Date to`
- a visual **Filter Builder**

Each filter row can include:
- **Scope**
  - `Chat`
  - `Message`
- **Field**
- **Operator**
- **Value**
- **Mode**
  - `Include`
  - `Exclude`

---

## Fields available in Advanced mode

### Chat fields
- `id`
- `name`
- `type`

### Message fields
- `id`
- `reply_to_message_id`
- `date`
- `from`
- `text`

---

## Operators available in Advanced mode

### Text fields
- `contains`
- `not contains`
- `equals`
- `not equals`
- `starts with`
- `ends with`

### Numeric fields
- `equals`
- `not equals`
- `greater than`
- `less than`

### Date fields
- `equals`
- `not equals`
- `on or after`
- `on or before`

---

## Output modes in Advanced mode

### `Full matching chats`
If a chat matches the filter rules, the full cleaned chat is included in the output.

### `Matched messages only`
If a chat matches, only the messages that actually match the message-level rules are included.

---

## Fields kept after cleaning

### Chat level
Only these fields are preserved:
- `id`
- `name`
- `messages`

### Message level
Only these fields are preserved:
- `id`
- `reply_to_message_id` — if present
- `date`
- `from`
- `text`

All other technical fields are removed.

---

## Output files

### `total_filtered.json`
A full current filtered snapshot across all uploaded files.

This is the main output file for the current run.

---

### `delta_updates.json`
Contains only:
- new chats;
- new messages in already existing chats

This file is useful when you only want to analyze changes compared to the previous run.

---

### `delta_full_chats.json`
Contains full versions only of chats that:
- appeared for the first time;
- or were updated since the previous run

This file is useful when you want to review the entire updated chat, not only the newly added messages.

---

### `processing_report.json`
Contains a processing report for the current run:
- how many files were uploaded;
- how many were processed successfully;
- how many failed;
- how many chats were found;
- how many remained after filtering;
- how many were excluded;
- how many were included in the final outputs.

---

## Delta logic

The application stores the previous full output snapshot in the `state` folder.

### Basic mode state
Basic mode keeps its own state separately.

### Advanced mode state
Advanced mode also keeps state separately, but **per automatically generated filter profile**.

That means:
- Basic mode does not overwrite Advanced mode history
- one Advanced filter configuration does not overwrite another Advanced configuration
- delta calculations stay isolated and correct

---

## Automatic Advanced profile isolation

Each Advanced configuration is normalized and converted into an automatic profile ID using a hash.

Because of that:
- the user does not need to enter a manual profile name;
- different advanced filter setups automatically get separate state history;
- delta comparison is always linked to the correct Advanced filter profile.

---

## What the Reset delta history button does

The **Reset delta history** button removes the current comparison history for the current mode/profile.

After that:
- the next run is treated as the first one;
- comparison with the previous total will no longer be available;
- delta files will be rebuilt from scratch.

In Advanced mode, reset applies to the current advanced profile only.

---

## Agent / webhook support

The project can send processed output files to an external agent through a webhook.

This is useful when, after filtering, you want to:
- send a file to AI;
- pass a file to n8n;
- trigger an external workflow;
- automate further analysis.

### How it works

Next to the main output files in the interface, there are **Send to agent** buttons.

When clicked:
1. the selected file is taken from local output;
2. its size is checked;
3. if the file size is within the configured limit, it is sent to the webhook;
4. if the file is too large, sending is blocked and a warning is shown.

### How the file is sent

The file is sent as `multipart/form-data`.

This means the receiving webhook gets the actual file, not just a JSON string placed directly into the request body.

This works well for:
- n8n
- Windmill
- standard webhook endpoints
- custom server-side automation flows

---

## File size limit

By default, the following limit is used:

```env
AGENT_MAX_FILE_SIZE_MB=16