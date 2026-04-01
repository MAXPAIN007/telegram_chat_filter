# Telegram Chat Filter

Telegram Chat Filter is a local tool for processing Telegram export JSON files.

The project is designed to:
- upload raw Telegram JSON exports;
- filter chats by keywords;
- clean messages from unnecessary technical fields;
- build convenient output JSON files for further analysis;
- optionally send already processed files to an external agent through a webhook.

The tool runs locally on the user's computer through a browser interface and a local Flask server.  
No data is sent anywhere automatically. External sending is only possible manually through the **Send to agent** button, if a webhook has been configured.

---

## What this project is for

Telegram exports contain a lot of extra fields and technical information that make analysis inconvenient.

This project solves several tasks at once:

1. Filters only the chats you need by given keywords.
2. Keeps only the useful fields in each message.
3. Builds convenient JSON files for manual review or AI analysis.
4. Creates a delta between the previous and current run.
5. Allows sending already prepared files to an external workflow, for example:
   - n8n
   - Windmill
   - a custom webhook
   - any other agent or automation pipeline

---

## What the project does

After uploading Telegram JSON files, the application:

1. reads the input Telegram export JSON files;
2. filters chats by keywords;
3. cleans the message payloads;
4. creates separate processed files for each uploaded JSON;
5. creates one combined full file;
6. compares the current combined file with the previous combined file;
7. creates update files;
8. stores the result for further work.

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

This file is useful when you want to see the whole updated chat, not only the newly added messages.

---

### `processing_report.json`
Contains a report for the current run:
- how many files were uploaded;
- how many were processed successfully;
- how many failed;
- how many chats were found;
- how many remained after filtering;
- how many were excluded;
- how many were included in the final output files.

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
1. the selected file is taken from the local output folder;
2. its size is checked;
3. if the file size is within the limit, it is sent to the configured webhook;
4. if the file is too large, sending is blocked and a warning is shown.

### How the file is sent
The file is sent as `multipart/form-data`.

This means the webhook receives the actual file, not just a raw JSON string inserted into the request body.

This format is convenient and reliable for:
- n8n
- Windmill
- standard webhook endpoints
- server-side processing pipelines

---

## File size limit

By default, the following limit is used:

```env
AGENT_MAX_FILE_SIZE_MB=16
````

If an output file is larger than this value, it will not be sent.

This is done for safety and compatibility with webhook systems that have incoming payload size limits.

---

## `.env` configuration

Create a `.env` file in the project root.

Example:

```env
AGENT_WEBHOOK_URL=
AGENT_AUTH_HEADER_NAME=
AGENT_AUTH_HEADER_VALUE=
AGENT_TIMEOUT_SECONDS=60
AGENT_MAX_FILE_SIZE_MB=16
```

### What these variables mean

#### `AGENT_WEBHOOK_URL`

The webhook URL where files will be sent.

Example:

```env
AGENT_WEBHOOK_URL=https://your-domain.com/webhook/telegram-agent
```

---

#### `AGENT_AUTH_HEADER_NAME`

Header name for authorization if the webhook requires a secret header.

Example:

```env
AGENT_AUTH_HEADER_NAME=X-Webhook-Secret
```

---

#### `AGENT_AUTH_HEADER_VALUE`

The value for that authorization header.

Example:

```env
AGENT_AUTH_HEADER_VALUE=my_secret_token
```

---

#### `AGENT_TIMEOUT_SECONDS`

HTTP request timeout when sending a file to the agent.

---

#### `AGENT_MAX_FILE_SIZE_MB`

Maximum allowed file size for sending.

---

## Example `.env`

```env
AGENT_WEBHOOK_URL=https://your-domain.com/webhook/telegram-agent
AGENT_AUTH_HEADER_NAME=X-Webhook-Secret
AGENT_AUTH_HEADER_VALUE=my_secret_token
AGENT_TIMEOUT_SECONDS=60
AGENT_MAX_FILE_SIZE_MB=16
```

---

## Installation and startup order

## 1. Clone or download the project

First, download the project to your computer or extract the archive into a separate folder.

---

## 2. Open the project folder

Open a terminal in the project folder.

Example for Git Bash:

```bash
cd /d/Projects/telegram_chat_filter
```

---

## 3. Create a virtual environment

```bash
python -m venv .venv
```

---

## 4. Activate the virtual environment

### For Git Bash

```bash
source .venv/Scripts/activate
```

### For PowerShell

```powershell
.venv\Scripts\Activate.ps1
```

---

## 5. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 6. Create `.env`

Create a `.env` file in the project root.

If you do not need webhook support yet, you can leave the values empty:

```env
AGENT_WEBHOOK_URL=
AGENT_AUTH_HEADER_NAME=
AGENT_AUTH_HEADER_VALUE=
AGENT_TIMEOUT_SECONDS=60
AGENT_MAX_FILE_SIZE_MB=16
```

If webhook support is needed, insert the real values.

---

## 7. Run the project

```bash
python app.py
```

Then open in the browser:

```text
http://127.0.0.1:5000
```

---

## How to use the interface

After opening the page:

1. Click **Choose files**
2. Select one or more Telegram export JSON files
3. Choose a filter mode:

   * `Include` — keep chats where a keyword is found
   * `Exclude` — remove chats where a keyword is found
4. Enter your keywords
5. Click **Run processing**
6. Download the output files you need
7. If needed, send one of the files through **Send to agent**

---

## How delta works

The project stores the previous full output file in the `state` folder.

It uses:

```text
state/previous_total_filtered.json
state/previous_total_meta.json
```

### On every new run

1. a new `total_filtered.json` is built;
2. the new total is compared with the previous total;
3. the following files are created:

   * `delta_updates.json`
   * `delta_full_chats.json`
4. the new total is stored as the current state for the next run

---

## What the Reset delta history button does

The **Reset delta history** button removes the current comparison history.

After that:

* the next run will be treated as the first one;
* comparison with the previous total will no longer be available;
* delta files will be rebuilt from scratch.

This is useful if you want to restart delta tracking from a clean state.

---

## Localization

The interface currently supports:

* Russian
* English

Language switching is available at the top of the page.

---

## Security

The project runs locally.

This means:

* Telegram JSON files are processed on the user's computer;
* data is not sent anywhere automatically;
* external sending happens only manually through **Send to agent**;
* secrets and webhook settings should be stored only in `.env`.

The `.env` file must not be committed to GitHub.

---

## What should not be uploaded to GitHub

Do not commit:

* `.env`
* `.venv`
* `output`
* `uploads`
* temporary and service files

---

## Project structure

```text
telegram_chat_filter/
├─ .venv/
├─ input/
├─ output/
├─ uploads/
├─ state/
├─ static/
│  ├─ app.js
│  └─ style.css
├─ templates/
│  └─ index.html
├─ app.py
├─ defaults.py
├─ delta_core.py
├─ parser_core.py
├─ requirements.txt
├─ README.md
├─ .env.example
└─ .gitignore
```

---

## Dependencies

Main project dependencies:

* Flask
* Werkzeug
* requests

They are installed automatically with:

```bash
pip install -r requirements.txt
```

---

## Possible future improvements

This project can be extended further, for example:

* add more interface languages;
* add output file archiving;
* add support for multiple webhook endpoints;
* add a preview mode before downloading;
* add more flexible filtering by `name` and `from`;
* add TXT / Markdown export;
* add batch sending to the agent.
