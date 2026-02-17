package container

import (
	"context"
	"fmt"
	"path/filepath"
	"time"

	"github.com/adam/runtime/internal/security"
)

type Sandbox struct {
	docker    *DockerManager
	profile   *security.Profile
	auditor   *security.Auditor
	baseImage string
}

func NewSandbox(docker *DockerManager, profile *security.Profile, auditor *security.Auditor) *Sandbox {
	return &Sandbox{
		docker:    docker,
		profile:   profile,
		auditor:   auditor,
		baseImage: "alpine:latest",
	}
}

func (s *Sandbox) SetBaseImage(image string) {
	s.baseImage = image
}

func (s *Sandbox) ExecuteScript(ctx context.Context, scriptPath string, args []string, env map[string]string) (*ExecutionResult, error) {
	guard := security.NewFileGuard(s.profile)
	allowed, resolved, reason := guard.ValidatePath(scriptPath, "read")
	if !allowed {
		s.auditor.Log("script_denied", map[string]interface{}{
			"path":   scriptPath,
			"reason": reason,
		})
		return nil, fmt.Errorf("script access denied: %s", reason)
	}

	mounts := map[string]string{
		filepath.Dir(resolved): "/workspace",
	}

	req := ExecutionRequest{
		Image:        s.baseImage,
		Command:      append([]string{"/workspace/" + filepath.Base(scriptPath)}, args...),
		Env:          env,
		WorkDir:      "/workspace",
		Mounts:       mounts,
		MemoryMB:     int64(s.profile.Container.MemoryLimitMB),
		CPULimit:     float64(s.profile.Container.CPULimitPercent) / 100,
		Timeout:      time.Duration(s.profile.Container.TimeoutSeconds) * time.Second,
		Network:      s.profile.Container.Network,
		ReadOnlyRoot: s.profile.Container.ReadOnlyRootfs,
	}

	if s.profile.Container.TimeoutSeconds == 0 {
		req.Timeout = 5 * time.Minute
	}

	if s.profile.Container.Runtime == "none" {
		return s.executeDirect(ctx, scriptPath, args, env)
	}

	s.auditor.Log("script_execute_start", map[string]interface{}{
		"path":  scriptPath,
		"args":  args,
		"image": s.baseImage,
	})

	result, err := s.docker.Execute(ctx, req)

	s.auditor.Log("script_execute_end", map[string]interface{}{
		"path":      scriptPath,
		"exit_code": result.ExitCode,
		"timed_out": result.TimedOut,
	})

	return result, err
}

func (s *Sandbox) executeDirect(ctx context.Context, scriptPath string, args []string, env map[string]string) (*ExecutionResult, error) {
	return &ExecutionResult{
		ExitCode: 1,
		Stderr:   "Direct execution not yet implemented. Use container mode.",
	}, nil
}
