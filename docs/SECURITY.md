# Adam Security Model

## Overview

Adam is designed with security as a core principle, not an afterthought. This document explains the security architecture and best practices.

## Threat Model

Adam assumes:
- The user's machine may have sensitive files
- Downloaded or generated code may be malicious
- API keys need protection from accidental exposure
- Memory may contain personal information

## Defense Layers

### Layer 1: Security Profiles

Three profiles provide different security levels:

**Balanced (Default)**
- Container: Docker
- File access: Limited to Documents, Projects, Desktop, Downloads
- Write access: Only ~/.adam/workspace
- Denied: ~/.ssh, ~/.gnupg, vault

**Paranoid**
- Container: Firecracker (microVM)
- File access: Explicit grants only
- Network: Disabled
- Shorter timeouts

**Permissive**
- Container: None
- File access: Full home (except private keys)
- Use only in trusted environments

### Layer 2: Container Isolation

Scripts run in isolated containers with:
- Read-only root filesystem
- No network access (by default)
- Memory and CPU limits
- Automatic cleanup after execution

### Layer 3: Encrypted Storage

**Vault**
- Fernet (AES-128-CBC) encryption
- PBKDF2 key derivation (480k iterations)
- Passphrase-protected
- File permissions: 600

**Database**
- SQLCipher optional
- Audit logs with tamper detection

### Layer 4: Path Validation

All file operations go through the runtime's FileGuard:
1. Path is resolved to absolute
2. Home directory (~) is expanded
3. Path is checked against denied list
4. Path is checked against allowed list
5. Operation (read/write) is validated

## Best Practices

### API Keys

```bash
# Store in vault, not config
adam vault add ANTHROPIC_API_KEY

# Never in environment or config files
```

### Profile Selection

```bash
# Use paranoid for untrusted code
adam profile set paranoid

# Use balanced for daily work
adam profile set balanced
```

### Audit Review

```bash
# Check audit logs periodically
cat ~/.adam/logs/audit.log
```

## Reporting Issues

Report security issues to security@example.com
