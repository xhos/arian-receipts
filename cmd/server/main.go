package main

import (
	"cmp"
	"flag"
	"fmt"
	"net"
	"os"
	"os/signal"
	"syscall"

	"github.com/charmbracelet/log"
	"github.com/ollama/ollama/api"
	"google.golang.org/grpc"
	"google.golang.org/grpc/health"
	"google.golang.org/grpc/health/grpc_health_v1"
	"google.golang.org/grpc/reflection"

	arianv1 "arian-receipts/internal/gen/arian/v1"
	"arian-receipts/internal/server"
)

func main() {
	port := flag.Int("port", 55556, "gRPC server port")
	jsonLogs := flag.Bool("json", false, "output logs as JSON")
	flag.Parse()

	logger := log.NewWithOptions(os.Stderr, log.Options{
		ReportTimestamp: true,
	})
	if *jsonLogs {
		logger.SetFormatter(log.JSONFormatter)
	}

	model := cmp.Or(os.Getenv("OLLAMA_MODEL"), "qwen2.5vl:3b")

	client, err := api.ClientFromEnvironment()
	if err != nil {
		logger.Fatal("failed to create ollama client", "err", err)
	}

	lis, err := net.Listen("tcp", fmt.Sprintf(":%d", *port))
	if err != nil {
		logger.Fatal("failed to listen", "err", err)
	}

	srv := grpc.NewServer()

	ocrService := server.New(client, model, logger)
	arianv1.RegisterReceiptOCRServiceServer(srv, ocrService)

	healthSrv := health.NewServer()
	healthSrv.SetServingStatus("", grpc_health_v1.HealthCheckResponse_SERVING)
	grpc_health_v1.RegisterHealthServer(srv, healthSrv)

	reflection.Register(srv)

	go func() {
		sigCh := make(chan os.Signal, 1)
		signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
		<-sigCh
		logger.Info("shutting down...")
		healthSrv.SetServingStatus("", grpc_health_v1.HealthCheckResponse_NOT_SERVING)
		srv.GracefulStop()
	}()

	logger.Info("server started", "port", *port, "model", model)
	if err := srv.Serve(lis); err != nil {
		logger.Fatal("serve failed", "err", err)
	}
}
