package security

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

type FileGuard struct {
	profile *Profile
}

func NewFileGuard(profile *Profile) *FileGuard {
	return &FileGuard{profile: profile}
}

func (fg *FileGuard) ValidatePath(requestedPath, operation string) (allowed bool, resolvedPath, reason string) {
	// Expand home directory FIRST, then get absolute path
	expandedPath := ExpandHome(requestedPath)
	absPath, err := filepath.Abs(expandedPath)
	if err != nil {
		return false, "", "cannot resolve path"
	}

	// Check denied list first (highest priority)
	for _, denied := range fg.profile.FileAccess.Denied {
		expanded := ExpandHome(denied)
		if expanded == "~" {
			// Special case: deny all home access
			home, _ := os.UserHomeDir()
			if strings.HasPrefix(absPath, home) {
				return false, absPath, "path is in denied list (all home access denied)"
			}
		} else if strings.HasPrefix(absPath, expanded) {
			return false, absPath, fmt.Sprintf("path is in denied list: %s", denied)
		}
	}

	// Check operation-specific allowed lists
	var allowedPaths []string
	switch operation {
	case "read":
		allowedPaths = fg.profile.FileAccess.Read
	case "write":
		allowedPaths = fg.profile.FileAccess.Write
	default:
		return false, absPath, fmt.Sprintf("unknown operation: %s", operation)
	}

	// Check if path matches any allowed path
	for _, allowed := range allowedPaths {
		expanded := ExpandHome(allowed)
		if expanded == "~" {
			// Special case: allow all home access
			home, _ := os.UserHomeDir()
			if strings.HasPrefix(absPath, home) {
				return true, absPath, ""
			}
		} else if strings.HasPrefix(absPath, expanded) {
			return true, absPath, ""
		}
	}

	// No match found
	return false, absPath, "path not in allowed list"
}

// ExpandHome expands ~ to the user's home directory
func ExpandHome(path string) string {
	if strings.HasPrefix(path, "~/") {
		home, _ := os.UserHomeDir()
		return filepath.Join(home, path[2:])
	}
	if path == "~" {
		home, _ := os.UserHomeDir()
		return home
	}
	return path
}
