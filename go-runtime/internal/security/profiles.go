package security

import (
	"fmt"
	"os"
	"path/filepath"

	"gopkg.in/yaml.v3"
)

type FileAccess struct {
	Read   []string `yaml:"read"`
	Write  []string `yaml:"write"`
	Denied []string `yaml:"denied"`
}

type ContainerConfig struct {
	Runtime         string `yaml:"runtime"`
	Network         bool   `yaml:"network"`
	ReadOnlyRootfs  bool   `yaml:"read_only_rootfs"`
	MemoryLimitMB   int    `yaml:"memory_limit_mb"`
	CPULimitPercent int    `yaml:"cpu_limit_percent"`
	TimeoutSeconds  int    `yaml:"timeout_seconds"`
	SeccompProfile  string `yaml:"seccomp_profile,omitempty"`
}

type AuditConfig struct {
	LogFileOps    bool `yaml:"log_file_ops"`
	LogShellCmds  bool `yaml:"log_shell_cmds"`
	LogModelCalls bool `yaml:"log_model_calls"`
	RetentionDays int  `yaml:"retention_days"`
	TamperEvident bool `yaml:"tamper_evident,omitempty"`
}

type Profile struct {
	Name        string          `yaml:"name"`
	Description string          `yaml:"description"`
	FileAccess  FileAccess      `yaml:"file_access"`
	Container   ContainerConfig `yaml:"container"`
	Audit       AuditConfig     `yaml:"audit"`
}

type ProfileManager struct {
	profilesDir string
	current     *Profile
}

func NewProfileManager(profilesDir string) *ProfileManager {
	if profilesDir == "" {
		home, _ := os.UserHomeDir()
		profilesDir = filepath.Join(home, ".adam", "profiles")
	}
	return &ProfileManager{profilesDir: profilesDir}
}

func (pm *ProfileManager) Load(name string) (*Profile, error) {
	path := filepath.Join(pm.profilesDir, name+".yaml")
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("failed to read profile %s: %w", name, err)
	}

	var profile Profile
	if err := yaml.Unmarshal(data, &profile); err != nil {
		return nil, fmt.Errorf("failed to parse profile %s: %w", name, err)
	}

	pm.current = &profile
	return &profile, nil
}

func (pm *ProfileManager) Current() *Profile {
	return pm.current
}

func (pm *ProfileManager) GetProfilesDir() string {
	return pm.profilesDir
}
