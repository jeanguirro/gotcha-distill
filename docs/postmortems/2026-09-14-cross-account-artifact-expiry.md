# Post-mortem: the 403 that was not a permission

**Date:** 2026-09-14
**Trigger:** hotfix redeploy of `api` release `v42` to production, 34 days
after `v42` was first built.
**Outcome:** `deploy:prod` failed for 52 minutes; for 45 of those the
production Lambda ran `v41` code with `v42-hotfix` configuration (the
`RELEASE` environment variable and a new timeout), because configuration was
updated before the code fetch failed. No customer-visible error; one internal
dashboard reported the wrong release for the duration.

## What happened

| UTC   | Event |
|-------|-------|
| 09:12 | Hotfix branch merged; `deploy:prod` starts in the prod account (`222222222222`) using the OIDC deploy role. |
| 09:13 | `aws lambda update-function-configuration --environment Variables={RELEASE=v42-hotfix}` succeeds. |
| 09:13 | `aws s3 cp s3://acme-build-artifacts/api/api-v42.zip ./api.zip` fails: `An error occurred (403) when calling the HeadObject operation: Forbidden`. Pipeline red. |
| 09:15 | Agent begins investigation. Reads 403 as an IAM denial. |
| 09:16–09:50 | Agent diffs the build account's (`111111111111`) bucket policy against the deploy role ARN, inspects the role's trust policy, runs `aws iam simulate-principal-policy` for `s3:GetObject` on the object ARN. Every result is `allowed`. Rollback to `v41` is attempted and fails with the identical 403 — `v41` was built 41 days ago. |
| 09:51 | Agent runs `aws s3api list-objects-v2 --bucket acme-build-artifacts --prefix api/` from the build account. `api-v42.zip` is absent. Oldest surviving object is 29 days old. |
| 09:53 | Lifecycle configuration on `acme-build-artifacts` shows `Expiration: Days=30` on prefix `api/`. Root cause identified. |
| 09:58 | `v42` rebuilt from the tagged commit, copied to a new prod-owned bucket, redeployed. Configuration and code consistent again. |
| 10:04 | Pipeline green. |

## The trigger: a 403 that was not a permission

The bucket policy on `acme-build-artifacts` granted the deploy role
`s3:GetObject` on `arn:aws:s3:::acme-build-artifacts/*`. It did not grant
`s3:ListBucket` on `arn:aws:s3:::acme-build-artifacts`. Without
`ListBucket`, S3 does not disclose whether a key exists: a `HeadObject` on a
missing key returns 403, exactly as it would on a key the caller is forbidden
to read. `simulate-principal-policy` was telling the truth — the role *was*
allowed to read the object. The object was gone.

The deletion was scheduled, not accidental. The build account's lifecycle rule
was added to control storage cost and was correct for its stated purpose,
ephemeral build outputs. Nobody had written down that the production deploy
read directly from that prefix, so the rule's blast radius was never
evaluated against the deploy path.

## Blind spots

**A 403 was interpreted before it was measured.** The first 35 minutes were
spent proving a hypothesis (IAM denial) that a single `list-objects-v2` would
have refuted in seconds. The error text was ambiguous by design; the agent
treated it as specific.

**The rollback depended on the same failing input.** Both forward and
backward paths read from the expiring prefix, so the moment one release aged
out, every older release had already aged out too. There was no path that
did not go through the missing bucket.

**Mutations ran before inputs were verified.** `update-function-configuration`
succeeded, then the artifact fetch failed. The deploy script had no
preflight; it assumed every step after the first would succeed because the
first did.

**Ownership of the artifact was not the deploying account's.** Production
depended on a bucket whose retention policy was set by another team for
another purpose. The lifecycle rule was visible in `infra/` of the *build*
repository, which the deploy agent never opened.

## What changed as a result

- `scripts/deploy.sh` now runs `aws s3api head-object` on the exact artifact
  before any mutation, and updates code before configuration.
- `scripts/promote.sh` copies the artifact from `acme-build-artifacts` to a
  prod-owned `acme-prod-release-artifacts` bucket at promotion time. The prod
  bucket has no expiration. `deploy.sh` reads only from it.
- The deploy role is granted `s3:ListBucket` on `acme-build-artifacts`
  (`infra/iam/deploy-role.tf`) so a missing key surfaces as 404, not 403.
- Two gotchas distilled into `docs/gotchas/infra-aws.md` and indexed in
  `AGENTS.md`, in the same commit as the code above:
  "Cross-account S3 answers 403 not 404 for a missing key" and
  "Never deploy from an artifact bucket you do not own".

## Still open

- Releases older than 30 days that were never promoted cannot be redeployed
  without a rebuild from tag. A backfill of the last 90 days of tags into the
  prod bucket is scheduled but not done.
- The build repository's lifecycle rule still applies to `api/`. It is
  correct there; the fix is that production no longer depends on it.
