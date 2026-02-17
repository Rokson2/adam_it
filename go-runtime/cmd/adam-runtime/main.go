package main

import (
	"flag"
	"fmt"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"

	"github.com/adam/runtime/internal/container"
	"github.com/adam/runtime/internal/rpc"
	"github.com/adam/runtime/internal/security"
)

var version = "0.1.0"

func main() {
	socketPath := flag.String("socket", "/tmp/adam-runtime.sock", "Unix socket path")
	profilesDir := flag.String("profiles", "", "Profiles directory")
	profile := flag.String("profile", "balanced", "Initial security profile")
	showVersion := flag.Bool("version", false, "Show version")
	flag.Parse()

	if *showVersion {
		fmt.Printf("Adam Runtime v%s\n", version)
		return
	}

	fmt.Printf("Starting Adam Runtime v%s...\n", version)

	pmDir := *profilesDir
	if pmDir == "" {
		home, _ := os.UserHomeDir()
		pmDir = filepath.Join(home, ".adam", "profiles")

		if _, err := os.Stat(pmDir); os.IsNotExist(err) {
			if _, err := os.Stat("profiles"); err == nil {
				pmDir = "profiles"
			}
		}
	}

	pm := security.NewProfileManager(pmDir)
	_, err := pm.Load(*profile)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Failed to load profile '%s': %v\n", *profile, err)
		fmt.Fprintf(os.Stderr, "Looking in: %s\n", pmDir)
		os.Exit(1)
	}
	fmt.Printf("Loaded profile: %s\n", *profile)

	docker, err := container.NewDockerManager()
	if err != nil {
		fmt.Printf("Warning: Docker not available: %v\n", err)
		fmt.Println("Some features will be limited.")
	}

	home, _ := os.UserHomeDir()
	auditLog := filepath.Join(home, ".adam", "logs", "audit.log")
	auditor := security.NewAuditor(auditLog, pm.Current().Audit.LogFileOps)

	var sandbox *container.Sandbox
	if docker != nil {
		sandbox = container.NewSandbox(docker, pm.Current(), auditor)
	}

	runtimeServer := rpc.NewRuntimeServer(pm, sandbox, auditor)
	server := rpc.NewServer()

	if err := server.Start(*socketPath, runtimeServer); err != nil {
		fmt.Fprintf(os.Stderr, "Failed to start server: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("Adam Runtime listening on %s\n", *socketPath)
	fmt.Println("Press Ctrl+C to stop")

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	<-sigCh

	fmt.Println("\nShutting down...")
	server.Stop()
	fmt.Println("Goodbye!")
}
