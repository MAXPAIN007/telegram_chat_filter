Ниже даю **обновлённый `README.md` целиком** с нормальной инструкцией:

* что нужно установить;
* что делать **при первом запуске**;
* что делать **при последующих запусках**;
* как настроить `.env`;
* как запустить проект локально.

Можешь просто полностью заменить содержимое `README.md`.

````md
# Telegram Chat Filter

Telegram Chat Filter is a local web tool for processing Telegram export JSON files.

It helps users:
- upload raw Telegram JSON exports;
- filter chats using either a simple or advanced filtering flow;
- remove unnecessary technical fields from messages;
- build clean, structured JSON files for manual analysis or AI processing;
- generate full snapshots and delta-based outputs;
- optionally send prepared files to an external agent through a webhook.

The application runs locally on the user's machine through a browser UI and a local Flask server.

No Telegram data is sent anywhere automatically.  
External sending only happens manually through the **Send to agent** button, if a webhook is configured.

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

## Output files

### `total_filtered.json`
A full current filtered snapshot across all uploaded files.

### `delta_updates.json`
Contains only:
- new chats
- new messages in already existing chats

### `delta_full_chats.json`
Contains full versions only of chats that:
- appeared for the first time
- or were updated since the previous run

### `processing_report.json`
Contains a report for the current run:
- how many files were uploaded
- how many were processed successfully
- how many failed
- how many chats were found
- how many remained after filtering
- how many were excluded
- how many were included in the final outputs

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
- visual **Filter Builder**

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

## Agent / webhook support

The project can send processed output files to an external agent through a webhook.

This is useful when, after filtering, you want to:
- send a file to AI
- pass a file to n8n
- trigger an external workflow
- automate further analysis

### How it works
Next to the main output files in the interface, there are **Send to agent** buttons.

When clicked:
1. the selected file is taken from local output
2. its size is checked
3. if the file size is within the configured limit, it is sent to the webhook
4. if the file is too large, sending is blocked and a warning is shown

### How the file is sent
The file is sent as `multipart/form-data`.

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
````

### Meaning of the variables

#### `AGENT_WEBHOOK_URL`

The webhook URL where files will be sent.

#### `AGENT_AUTH_HEADER_NAME`

Header name for authorization, if the webhook requires a secret header.

#### `AGENT_AUTH_HEADER_VALUE`

The value for that authorization header.

#### `AGENT_TIMEOUT_SECONDS`

HTTP timeout when sending a file to the agent.

#### `AGENT_MAX_FILE_SIZE_MB`

Maximum allowed file size for sending.

If you do not need webhook support yet, you can keep the values empty.

---

# Quick start for new users

## Requirements

Before running the project, make sure you have installed:

* **Python 3.10+**
* **Git** (optional, but recommended if cloning from GitHub)

To check Python:

```bash
python --version
```

---

## First run

### 1. Clone the repository or download it

Using Git:

```bash
git clone <YOUR_REPOSITORY_URL>
cd telegram_chat_filter
```

Or download the ZIP archive from GitHub and extract it, then open a terminal inside the project folder.

---

### 2. Create a virtual environment

```bash
python -m venv .venv
```

---

### 3. Activate the virtual environment

#### Git Bash

```bash
source .venv/Scripts/activate
```

#### PowerShell

```powershell
.venv\Scripts\Activate.ps1
```

#### CMD

```cmd
.venv\Scripts\activate.bat
```

---

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

---

### 5. Create `.env`

Create a `.env` file in the project root.

Minimal example:

```env
AGENT_WEBHOOK_URL=
AGENT_AUTH_HEADER_NAME=
AGENT_AUTH_HEADER_VALUE=
AGENT_TIMEOUT_SECONDS=60
AGENT_MAX_FILE_SIZE_MB=16
```

If you do not need agent/webhook integration yet, leave the values empty.

---

### 6. Run the application

```bash
python app.py
```

After that, open in your browser:

```text
http://127.0.0.1:5000
```

---

## Next runs

After the first setup, you do **not** need to reinstall everything every time.

For normal daily use:

### Git Bash

```bash
cd /path/to/telegram_chat_filter
source .venv/Scripts/activate
python app.py
```

### PowerShell

```powershell
cd path\to\telegram_chat_filter
.venv\Scripts\Activate.ps1
python app.py
```

### CMD

```cmd
cd path\to\telegram_chat_filter
.venv\Scripts\activate.bat
python app.py
```

Then open:

```text
http://127.0.0.1:5000
```

---

## If dependencies were updated

If the repository was updated and `requirements.txt` changed, run again:

```bash
pip install -r requirements.txt
```

---

## How to use the interface

1. Open the local app in your browser
2. Choose one or more Telegram export JSON files
3. Select the processing mode:

   * `Basic`
   * `Advanced`
4. Configure filters
5. Click **Run processing**
6. Download the output files you need
7. If necessary, click **Send to agent** to pass a file into an external workflow

---

## Reset delta history

The **Reset delta history** button removes the current comparison history for the current mode/profile.

After that:

* the next run is treated as the first one
* comparison with the previous total will no longer be available
* delta files will be rebuilt from scratch

In Advanced mode, reset applies to the current advanced profile only.

---

## Localization

The UI currently supports:

* Russian
* English

Language switching is available in the header.

---

## Security

The project runs locally.

This means:

* Telegram JSON files are processed on the user's machine
* data is not sent anywhere automatically
* external sending happens only manually through **Send to agent**
* secrets and webhook settings should be stored only in `.env`

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
├─ parser_core.py
├─ delta_core.py
├─ advanced_core.py
├─ profile_state.py
├─ requirements.txt
├─ README.md
├─ .env.example
└─ .gitignore
```

---

## Dependencies

Main dependencies:

* Flask
* Werkzeug
* requests

Install them with:

```bash
pip install -r requirements.txt
```
