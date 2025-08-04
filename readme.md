# arian‑receipts

a microservice designed for use inside the arian ecosystem, but repurposable. it provides a simple grpc api to parse receipts using google gemini or a local pipeline (poc).

```shell
export GOOGLE_API_KEY="your-api-key-here"
uv run arian-receipts
# INFO app.app — starting gRPC server
# INFO app.app — gRPC server ready
```

## grpc api reference

### `arian.v1.ReceiptParsingService/ParseImage`

parses a receipt image and returns structured data.

```shell
# using grpcurl with base64 encoded image
grpcurl -plaintext \
  -d '{
    "image_data": "'$(base64 -w0 receipt.jpg)'",
    "content_type": "image/jpeg"
  }' \
  localhost:50051 \
  arian.v1.ReceiptParsingService/ParseImage
```

response example:

```json
{
  "receipt": {
    "merchant": "NOFRILLS",
    "total_amount": {
      "currency_code": "USD",
      "units": "18",
      "nanos": 870000000
    },
    "items": [
      {
        "name": "PC CHO COOKIE",
        "quantity": 1,
        "unit_price": {
          "currency_code": "USD",
          "units": "4",
          "nanos": 790000000
        }
      }
    ]
  }
}
```

### `arian.v1.ReceiptParsingService/GetStatus`

returns provider availability (also serves as health check).

```shell
grpcurl -plaintext -d '{}' localhost:50051 arian.v1.ReceiptParsingService/GetStatus
```

response example:

```json
{
  "providers": [
    {
      "name": "gemini",
      "kind": "remote", 
      "available": true,
      "model": "gemini-2.0-flash-001"
    },
    {
      "name": "local",
      "kind": "local",
      "available": false,
      "reason": "tesseract not found on PATH"
    }
  ],
  "service_version": "0.3.0"
}
```

## configuration

| variable        | default  | description                           |
|-----------------|----------|---------------------------------------|
| `GOOGLE_API_KEY`| required | google ai api key for gemini          |
| `GRPC_PORT`     | `50051`  | grpc server port                      |
| `MAX_UPLOAD_MB` | `10`     | maximum file size                     |
| `LOG_LEVEL`     | `INFO`   | logging level                         |

## providers

there are 2 existing providers (easily extended):

1. **gemini**: uses google gemini api (requires `GOOGLE_API_KEY` in env).  
2. **local**: poc with tesseract + llama. install local extras (`.[local]`) and ensure `tesseract` on PATH.

## arian ecosystem

- [arian](https://github.com/xhos/arian): web dashboard  
- [ariand](https://github.com/xhos/ariand): backend service  
- [arian-parser](https://github.com/xhos/arian-parser): transaction email parser
