# arian-receipts

a microservice designed for use inside the arian ecosystem, but can be repurposed for other uses. it simply provides an api to parse receipts using either a local pipilne or gemini.

## api reference

### parse receipt

**endpoint**: `POST /parse`

Parses a receipt image and returns structured data.

**request**:
- content-Type: `multipart/form-data`
- body: `file` - image file of a receipt (JPEG or PNG)

**response**:
```json
{
  "merchant": "STORE NAME",
  "date": "YYYY-MM-DD",
  "total": 99.99,
  "items": [
    {
      "name": "PRODUCT NAME",
      "price": 19.99,
      "qty": 1
    }
  ]
}
```

### health

**endpoint**:  GET /health

**response**:

```json
{
  "status": "ok"
}
```

## note

there are 2 existing providers (can be easily extended):

1. gemini: uses google's gemini api for high-accuracy parsing. it works surprisingly well. requires a `GEMINI_API_KEY` environment variable, if it's set, the project uses it, to use local unset the var. absolutely not private (from google).

2. local: a proof-of-concept implementation using local ocr and a small llm. uses tesseract for text extraction and phi-3-mini for parsing. the local implementation is experimental and not ready for actual use. but hey, it's private! dig thru the code if you want to see how to properly configure and use it.

## arian ecosystem
- [arian](https://github.com/xhos/arian): web dashboard
- [ariand](https://github.com/xhos/ariand): backend service
- [arian-parser](https://github.com/xhos/arian-parser): transaction email parser
