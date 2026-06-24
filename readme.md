# Synology NAS FastAPI Integration

## Overview

This project provides a FastAPI-based API for interacting with a Synology NAS using the Synology FileStation API.

The service supports:

* Authentication with Synology NAS
* Folder creation
* Single file upload
* Multiple file upload
* Nested directory uploads
* Custom destination uploads
* File preview streaming
* File downloads
* Session management

---

## Features

### Authentication

* Login to Synology NAS
* Session ID caching
* Logout support
* Automatic session reset on failures

### File Management

* Create folders dynamically
* Upload files to specified locations
* Upload multiple files in a single request
* Create parent directories automatically

### File Access

* Stream files directly from NAS
* Preview PDFs and images
* Download files from NAS

---

## Project Structure

```text
.
├── main.py
├── requirements.txt
├── .env
├── .gitignore
└── README.md
```

---

## Requirements

* Python 3.10+
* Synology NAS with FileStation enabled
* DSM account with FileStation permissions

---

## Installation

### Clone Repository

```bash
git clone https://github.com/<your-username>/<repository-name>.git

cd <repository-name>
```

### Create Virtual Environment

```bash
python -m venv nev
```

### Activate Environment

Linux / macOS:

```bash
source nev/bin/activate
```

Windows:

```bash
nev\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Environment Configuration

Create a `.env` file:

```env
SYNOLOGY_BASE_URL=https://your-nas-url
SYNOLOGY_USERNAME=your-username
SYNOLOGY_PASSWORD=your-password
DEFAULT_ROOT_FOLDER=/base-directory
```

Example using `python-dotenv`:

```python
from dotenv import load_dotenv
import os

load_dotenv()

SYNOLOGY_BASE_URL = os.getenv("SYNOLOGY_BASE_URL")
SYNOLOGY_USERNAME = os.getenv("SYNOLOGY_USERNAME")
SYNOLOGY_PASSWORD = os.getenv("SYNOLOGY_PASSWORD")
DEFAULT_ROOT_FOLDER = os.getenv("DEFAULT_ROOT_FOLDER")
```

---

## Running the Application

```bash
uvicorn main:app --reload
```

Application URL:

```text
http://localhost:8000
```

Swagger Documentation:

```text
http://localhost:8000/docs
```

ReDoc Documentation:

```text
http://localhost:8000/redoc
```

---

## API Endpoints

### Authentication

| Method | Endpoint        |
| ------ | --------------- |
| GET    | /nas/login-test |
| POST   | /nas/logout     |

### Folder Operations

| Method | Endpoint           |
| ------ | ------------------ |
| POST   | /nas/create-folder |

### Upload Operations

| Method | Endpoint             |
| ------ | -------------------- |
| POST   | /nas/upload/direct   |
| POST   | /nas/upload/multiple |
| POST   | /nas/upload/nested   |
| POST   | /nas/upload/custom   |

### File Access

| Method | Endpoint            |
| ------ | ------------------- |
| GET    | /nas/preview-stream |
| GET    | /nas/download       |

---

## Example Upload Request

```bash
curl -X POST \
  "http://localhost:8000/nas/upload/custom" \
  -F "destination_folder=/documents" \
  -F "file=@sample.pdf"
```

---

## Security Notes

* Never commit `.env` files.
* Never expose NAS credentials.
* Restrict NAS permissions to required folders only.
* Consider enabling SSL certificate validation instead of using `verify=False` in production.

---

## Future Improvements

* JWT Authentication
* Folder listing endpoint
* File deletion endpoint
* File metadata endpoint
* Better session persistence
* Retry mechanism for NAS requests

---

## License

MIT License
