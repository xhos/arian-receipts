package main

import (
	"flag"
	"fmt"
	"log"
	"net"
	"os"
	"os/signal"
	"syscall"

	arianv1 "arian-receipts/internal/gen/arian/v1"
	"arian-receipts/internal/server"

	"github.com/ollama/ollama/api"
	"google.golang.org/grpc"
	"google.golang.org/grpc/health"
	"google.golang.org/grpc/health/grpc_health_v1"
	"google.golang.org/grpc/reflection"
)

func main() {
	port := flag.Int("port", 50051, "gRPC server port")
	flag.Parse()

	model := envOr("OLLAMA_MODEL", "qwen2.5vl:3b")

	// ollama client reads OLLAMA_HOST env (defaults to http://127.0.0.1:11434)
	client, err := api.ClientFromEnvironment()
	if err != nil {
		log.Fatalf("failed to create ollama client: %v", err)
	}

	lis, err := net.Listen("tcp", fmt.Sprintf(":%d", *port))
	if err != nil {
		log.Fatalf("failed to listen: %v", err)
	}

	srv := grpc.NewServer()

	ocrService := server.New(client, model)
	arianv1.RegisterReceiptOCRServiceServer(srv, ocrService)

	healthSrv := health.NewServer()
	healthSrv.SetServingStatus("", grpc_health_v1.HealthCheckResponse_SERVING)
	grpc_health_v1.RegisterHealthServer(srv, healthSrv)

	reflection.Register(srv)

	go func() {
		sigCh := make(chan os.Signal, 1)
		signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
		<-sigCh
		log.Println("shutting down...")
		healthSrv.SetServingStatus("", grpc_health_v1.HealthCheckResponse_NOT_SERVING)
		srv.GracefulStop()
	}()

	log.Printf("listening on :%d (model: %s)", *port, model)
	if err := srv.Serve(lis); err != nil {
		log.Fatalf("failed to serve: %v", err)
	}
}

func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
