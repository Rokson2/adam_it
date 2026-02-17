package container

import (
	"context"
	"fmt"
	"io"
	"time"

	"github.com/docker/docker/api/types/container"
	"github.com/docker/docker/api/types/image"
	"github.com/docker/docker/client"
)

type ExecutionRequest struct {
	Image        string            `json:"image"`
	Command      []string          `json:"command"`
	Env          map[string]string `json:"env"`
	WorkDir      string            `json:"work_dir"`
	Mounts       map[string]string `json:"mounts"`
	MemoryMB     int64             `json:"memory_mb"`
	CPULimit     float64           `json:"cpu_limit"`
	Timeout      time.Duration     `json:"timeout"`
	Network      bool              `json:"network"`
	ReadOnlyRoot bool              `json:"read_only_root"`
}

type ExecutionResult struct {
	ExitCode int    `json:"exit_code"`
	Stdout   string `json:"stdout"`
	Stderr   string `json:"stderr"`
	TimedOut bool   `json:"timed_out"`
}

type DockerManager struct {
	client *client.Client
}

func NewDockerManager() (*DockerManager, error) {
	cli, err := client.NewClientWithOpts(client.FromEnv, client.WithAPIVersionNegotiation())
	if err != nil {
		return nil, fmt.Errorf("failed to create docker client: %w", err)
	}
	return &DockerManager{client: cli}, nil
}

func (dm *DockerManager) Execute(ctx context.Context, req ExecutionRequest) (*ExecutionResult, error) {
	config := &container.Config{
		Image:      req.Image,
		Cmd:        req.Command,
		Env:        envMapToSlice(req.Env),
		WorkingDir: req.WorkDir,
		Tty:        false,
	}

	hostConfig := &container.HostConfig{
		AutoRemove: true,
		Resources: container.Resources{
			Memory:   req.MemoryMB * 1024 * 1024,
			NanoCPUs: int64(req.CPULimit * 1e9),
		},
		ReadonlyRootfs: req.ReadOnlyRoot,
	}

	for hostPath, containerPath := range req.Mounts {
		hostConfig.Binds = append(hostConfig.Binds,
			fmt.Sprintf("%s:%s:ro", hostPath, containerPath))
	}

	if !req.Network {
		hostConfig.NetworkMode = "none"
	}

	resp, err := dm.client.ContainerCreate(ctx, config, hostConfig, nil, nil, "")
	if err != nil {
		return nil, fmt.Errorf("failed to create container: %w", err)
	}

	if err := dm.client.ContainerStart(ctx, resp.ID, container.StartOptions{}); err != nil {
		return nil, fmt.Errorf("failed to start container: %w", err)
	}

	statusCh, errCh := dm.client.ContainerWait(ctx, resp.ID, container.WaitConditionNotRunning)

	var exitCode int64
	timedOut := false

	select {
	case err := <-errCh:
		if err != nil {
			return nil, fmt.Errorf("container error: %w", err)
		}
	case status := <-statusCh:
		exitCode = status.StatusCode
	case <-time.After(req.Timeout):
		timeout := 5
		dm.client.ContainerStop(ctx, resp.ID, container.StopOptions{Timeout: &timeout})
		timedOut = true
		exitCode = 137
	}

	stdout, stderr := dm.getLogs(ctx, resp.ID)

	return &ExecutionResult{
		ExitCode: int(exitCode),
		Stdout:   stdout,
		Stderr:   stderr,
		TimedOut: timedOut,
	}, nil
}

func (dm *DockerManager) getLogs(ctx context.Context, containerID string) (string, string) {
	out, err := dm.client.ContainerLogs(ctx, containerID, container.LogsOptions{
		ShowStdout: true,
		ShowStderr: true,
	})
	if err != nil {
		return "", ""
	}
	defer out.Close()

	data, err := io.ReadAll(out)
	if err != nil {
		return "", ""
	}

	return string(data), ""
}

func (dm *DockerManager) IsAvailable() bool {
	_, err := dm.client.Ping(context.Background())
	return err == nil
}

func (dm *DockerManager) PullImage(ctx context.Context, img string) error {
	reader, err := dm.client.ImagePull(ctx, img, image.PullOptions{})
	if err != nil {
		return fmt.Errorf("failed to pull image: %w", err)
	}
	defer reader.Close()

	_, err = io.Copy(io.Discard, reader)
	return err
}

func envMapToSlice(m map[string]string) []string {
	var result []string
	for k, v := range m {
		result = append(result, fmt.Sprintf("%s=%s", k, v))
	}
	return result
}
