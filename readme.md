# arian-receipts

stateless, small gRPC service that parses receipt images using Qwen2.5-VL via Ollama.

## usage

```bash
# start ollama with the model
ollama pull qwen2.5vl:3b

# run the server (default port 50051)
go run ./cmd/server -port 50051
```

## configuration

| Flag | Default | Description |
|------|---------|-------------|
| `-port` | 50051 | gRPC listen port |

| Env | Default | Description |
|-----|---------|-------------|
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Ollama API URL |
| `OLLAMA_MODEL` | `qwen2.5vl:3b` | Model name |

## proto

See `proto/arian/v1/receipt_ocr.proto` for the service definition.

```protobuf
service ReceiptOCRService {
  rpc ParseReceipt(ParseReceiptRequest) returns (ParseReceiptResponse);
  rpc Health(HealthRequest) returns (HealthResponse);
}
```

## development

```bash
# test cli for local model testing
go run cmd/test-cli/main.go image.jpg

# regenerate protos
buf generate
```
