# arian‑receipts

a microservice designed for use inside the arian ecosystem, but repurposable. it provides a simple api to parse receipts using google gemini or a local pipeline (poc).

## api reference

### POST /v1/providers/{provider}/parse

Parses a receipt image and returns structured data.

#### request

- content‑type: multipart/form‑data  
- body: `file` – image of receipt (jpeg|png, ≤10 MB)

```shell
curl -sS \
  -F "file=@image.jpg;type=image/jpeg" \
  http://localhost:8000/v1/providers/gemini/parse | jq .
```

#### response

```json
{
  "total": 99.99,
  "items": [
    {"name":"PRODUCT NAME","price":19.99,"qty":1}
  ],
  "merchant": "STORE NAME",
  "date": "YYYY-MM-DD"
}
```

### GET /v1/providers

returns state of each provider (model, availability)

```shell
curl -s http://localhost:8000/v1/providers | jq .
```

example:

```json
[
  {
    "name":"gemini",
    "kind":"remote",
    "available":true,
    "reason":null,
    "model":"gemini-2.0-flash-001"
  },
  {
    "name":"local",
    "kind":"local",
    "available":false,
    "reason":"missing local extras: No module named 'pytesseract'",
    "model":null
  }
]
```

### GET /v1/health

returns basic health status

```shell
curl -s http://localhost:8000/v1/health | jq .
```

#### response

```json
{"status":"ok"}
```

```shell
curl -s http://localhost:8000/v1/health | jq .
```

#### response

```json
{"status":"ok"}
```

## note

there are 2 existing providers (easily extended):

1. **gemini**: uses google gemini api (requires `GOOGLE_API_KEY` in env).  
2. **local**: poc with tesseract + llama. install local extras (`.[local]`) and ensure `tesseract` on PATH.

## arian ecosystem

- [arian](https://github.com/xhos/arian): web dashboard  
- [ariand](https://github.com/xhos/ariand): backend service  
- [arian-parser](https://github.com/xhos/arian-parser): transaction email parser
