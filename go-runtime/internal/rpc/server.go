package rpc

import (
	"context"
	"fmt"
	"net"
	"os"

	pb "github.com/adam/runtime/proto"
	"github.com/adam/runtime/internal/container"
	"github.com/adam/runtime/internal/security"

	"google.golang.org/grpc"
)

type RuntimeServer struct {
	pb.UnimplementedRuntimeServiceServer

	profileManager *security.ProfileManager
	sandbox        *container.Sandbox
	auditor        *security.Auditor
}

func NewRuntimeServer(pm *security.ProfileManager, sandbox *container.Sandbox, auditor *security.Auditor) *RuntimeServer {
	return &RuntimeServer{
		profileManager: pm,
		sandbox:        sandbox,
		auditor:        auditor,
	}
}

func (s *RuntimeServer) ExecuteScript(ctx context.Context, req *pb.ScriptRequest) (*pb.ScriptResponse, error) {
	s.auditor.Log("execute_script_request", map[string]interface{}{
		"script_path": req.ScriptPath,
		"args":        req.Args,
	})

	result, err := s.sandbox.ExecuteScript(ctx, req.ScriptPath, req.Args, req.Env)
	if err != nil {
		s.auditor.Log("execute_script_error", map[string]interface{}{
			"error": err.Error(),
		})
		return &pb.ScriptResponse{
			ExitCode: 1,
			Stderr:   err.Error(),
		}, nil
	}

	return &pb.ScriptResponse{
		ExitCode: int32(result.ExitCode),
		Stdout:   result.Stdout,
		Stderr:   result.Stderr,
		TimedOut: result.TimedOut,
	}, nil
}

func (s *RuntimeServer) ValidatePath(ctx context.Context, req *pb.PathRequest) (*pb.PathResponse, error) {
	profile := s.profileManager.Current()
	if profile == nil {
		return &pb.PathResponse{
			Allowed:      false,
			DenialReason: "no profile loaded",
		}, nil
	}

	guard := security.NewFileGuard(profile)
	allowed, resolved, reason := guard.ValidatePath(req.Path, req.Operation)

	return &pb.PathResponse{
		Allowed:      allowed,
		ResolvedPath: resolved,
		DenialReason: reason,
	}, nil
}

func (s *RuntimeServer) GetProfile(ctx context.Context, req *pb.ProfileRequest) (*pb.ProfileResponse, error) {
	profile := s.profileManager.Current()
	if profile == nil {
		return nil, fmt.Errorf("no profile loaded")
	}

	return &pb.ProfileResponse{
		Name: profile.Name,
	}, nil
}

func (s *RuntimeServer) SetProfile(ctx context.Context, req *pb.SetProfileRequest) (*pb.ProfileResponse, error) {
	profile, err := s.profileManager.Load(req.ProfileName)
	if err != nil {
		return nil, err
	}

	s.auditor.Log("profile_changed", map[string]interface{}{
		"profile": profile.Name,
	})

	return &pb.ProfileResponse{
		Name: profile.Name,
	}, nil
}

func (s *RuntimeServer) GetStatus(ctx context.Context, req *pb.StatusRequest) (*pb.StatusResponse, error) {
	profile := s.profileManager.Current()
	profileName := ""
	if profile != nil {
		profileName = profile.Name
	}

	return &pb.StatusResponse{
		RuntimeHealthy:   true,
		ActiveContainers: 0,
		CurrentProfile:   profileName,
	}, nil
}

type Server struct {
	grpcServer *grpc.Server
	listener   net.Listener
}

func NewServer() *Server {
	return &Server{}
}

func (s *Server) Start(socketPath string, runtimeServer *RuntimeServer) error {
	os.Remove(socketPath)

	dir := ""
	for i := len(socketPath) - 1; i >= 0; i-- {
		if socketPath[i] == '/' {
			dir = socketPath[:i]
			break
		}
	}
	if dir != "" {
		os.MkdirAll(dir, 0755)
	}

	listener, err := net.Listen("unix", socketPath)
	if err != nil {
		return fmt.Errorf("failed to listen: %w", err)
	}
	s.listener = listener

	s.grpcServer = grpc.NewServer()
	pb.RegisterRuntimeServiceServer(s.grpcServer, runtimeServer)

	go s.grpcServer.Serve(listener)

	return nil
}

func (s *Server) Stop() {
	if s.grpcServer != nil {
		s.grpcServer.GracefulStop()
	}
}
