# DeepSeek GitHub Operating Contract

## Source of Truth

GitHub private repository is the formal source of truth.

Local folders are working copies.

ZIP is no longer the normal external-audit transport.

## Main

`main` means:

> latest code accepted by External Audit.

DeepSeek must not directly develop on `main`.

## Development

Use:

```text
ds/<stage>
fix/<audit-finding>
```

For safety fixes, prefer:

```text
failing reproduction commit
→ production fix
→ adversarial coverage
→ docs/audit
```

## Pull Request

PR is the audit unit.

Audit identity is:

```text
repository
base SHA
head SHA
PR number
```

When status becomes:

```text
READY FOR EXTERNAL AUDIT
```

the Head SHA is frozen.

Any new commit invalidates the previous external review.

## Internal Audit

Before external review:

```text
P0 = 0
P1 = 0
full regression = PASS
focused adversarial = PASS
deterministic concurrency = PASS
required stress = PASS
CI = PASS
docs consistent = PASS
```

DeepSeek may only declare:

```text
READY FOR EXTERNAL AUDIT
```

Never self-declare CLOSED.

## Approval

After external approval:

```text
merge PR
→ main
→ immutable audit-approved/<stage> tag
```

## Secrets

Never commit or report:

- `.env`
- API keys
- GitHub PAT
- passwords
- SSH private keys
- credentials

If a secret ever enters Git history:

1. rotate/revoke it first;
2. stop pushing;
3. clean history;
4. re-scan;
5. continue only after verification.
