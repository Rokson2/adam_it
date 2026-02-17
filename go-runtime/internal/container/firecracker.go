package container

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"time"
)

// FirecrackerManager manages Firecracker microVM execution
type FirecrackerManager struct {
	socketDir  string
	kernelPath string
	rootfsPath string
}

// NewFirecrackerManager creates a new Firecracker manager
func NewFirecrackerManager() (*FirecrackerManager, error) {
	if _, err := exec.LookPath("firecracker"); err != nil {
		return nil, fmt.Errorf("firecracker not found: %w", err)
	}

	socketDir := "/tmp/firecracker-sockets"
	os.MkdirAll(socketDir, 0755)

	return &FirecrackerManager{
		socketDir:  socketDir,
		kernelPath: "/var/lib/adam/vmlinux",
		rootfsPath: "/var/lib/adam/rootfs.ext4",
	}, nil
}

// IsAvailable checks if Firecracker is available
func (fm *FirecrackerManager) IsAvailable() bool {
	_, err := exec.LookPath("firecracker")
	return err == nil
}

// Execute runs a command in a Firecracker microVM
func (fm *FirecrackerManager) Execute(ctx context.Context, req ExecutionRequest) (*ExecutionResult, error) {
	vmID := fmt.Sprintf("adam-%d", time.Now().UnixNano())
	socketPath := filepath.Join(fm.socketDir, vmID+".sock")

	config := fm.createVMConfig(req, vmID)
	configPath := filepath.Join(fm.socketDir, vmID+".json")
	if err := os.WriteFile(configPath, []byte(config), 0644); err != nil {
		return nil, fmt.Errorf("failed to write VM config: %w", err)
	}
	defer os.Remove(configPath)

	cmd := exec.CommandContext(ctx, "firecracker",
		"--api-sock", socketPath,
		"--config-file", configPath,
	)

	output, err := cmd.CombinedOutput()

	os.Remove(socketPath)

	if err != nil {
		if ctx.Err() == context.DeadlineExceeded {
			return &ExecutionResult{
				ExitCode: 137,
				Stderr:   "VM execution timed out",
				TimedOut: true,
			}, nil
		}
		return &ExecutionResult{
			ExitCode: 1,
			Stderr:   string(output),
		}, nil
	}

	return &ExecutionResult{
		ExitCode: 0,
		Stdout:   string(output),
	}, nil
}

// createVMConfig generates Firecracker VM configuration
func (fm *FirecrackerManager) createVMConfig(req ExecutionRequest, vmID string) string {
	memoryMB := req.MemoryMB
	if memoryMB == 0 {
		memoryMB = 256
	}

	return fmt.Sprintf(`{
		"boot-source": {
			"kernel_image_path": "%s",
			"boot_args": "console=ttyS0 reboot=k panic=1 pci=off"
		},
		"drives": [
			{
				"drive_id": "rootfs",
				"path_on_host": "%s",
				"is_root_device": true,
				"is_read_only": true
			}
		],
		"machine-config": {
			"vcpu_count": 1,
			"mem_size_mib": %d
		}
	}`, fm.kernelPath, fm.rootfsPath, memoryMB)
}

// SetupImages prepares kernel and rootfs images for Firecracker
func SetupImages(kernelPath, rootfsPath string) error {
	if _, err := os.Stat(kernelPath); os.IsNotExist(err) {
		return fmt.Errorf("kernel image not found at %s", kernelPath)
	}
	if _, err := os.Stat(rootfsPath); os.IsNotExist(err) {
		return fmt.Errorf("rootfs image not found at %s", rootfsPath)
	}
	return nil
}
