# arian-receipts

stateless, small gRPC mircoservice that parses receipt images using Qwen2.5-VL via Ollama.

## usage

```bash
ollama pull qwen2.5vl:3b

go run ./cmd/server
```

## configuration

| flag    | default | description          |
|---------|---------|----------------------|
| `-port` | 55556   | gRPC listen port     |
| `-json` | false   | JSON structured logs |

| env            | default                  | description    |
|----------------|--------------------------|----------------|
| `OLLAMA_HOST`  | `http://127.0.0.1:11434` | Ollama API URL |
| `OLLAMA_MODEL` | `qwen2.5vl:3b`           | Model name     |

## proto

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
```

to regenerate proto code:

```bash
regen
```
