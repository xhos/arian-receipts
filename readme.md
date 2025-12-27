# arian‑receipts

## development

### local model testing

```bash
ollama pull qwen2.5vl:3b
go run cmd/test-cli/main.go image.jpg
# you can also do `go run cmd/test-cli/main.go *.jpg`
```

to change the model, adjust the const in `cmd/test-cli/main.go`
