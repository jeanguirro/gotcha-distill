# Gotchas — infra & AWS (deploy pipeline, artifact buckets, cross-account IAM)

Read BEFORE touching `infra/`, deploy workflows, artifact buckets, or any
cross-account IAM: S3 error semantics, artifact ownership, deploy ordering.

Lazy-loaded gotcha file: `AGENTS.md` carries the one-line trigger index; the
full stories live here. Every entry cost production or a near-miss. Add new
gotchas here AND add their index line to `AGENTS.md` in the same commit.

## Cross-account S3 answers 403 not 404 for a missing key

**A cross-account `HeadObject` or `GetObject` on a key that does not exist
  returns `403 Forbidden`, not `404 Not Found`** (2026-09-14, cost a
  35-minute IAM detour and one half-applied production deploy — see
  `docs/postmortems/2026-09-14-cross-account-artifact-expiry.md`): S3 only
  discloses "not found" to callers that hold `s3:ListBucket` on the bucket,
  and a bucket policy that grants `s3:GetObject` on `arn:aws:s3:::bucket/*`
  says nothing about the bucket ARN itself. The deploy role had exactly that
  grant, the artifact `api/api-v42.zip` had been expired by the build
  account's 30-day lifecycle rule, and the resulting 403 sent the agent into
  the bucket policy, the role trust policy and `simulate-principal-policy`
  (all green) before anyone listed the prefix. Fix: grant the deploy role
  `s3:ListBucket` on the build bucket so a missing key surfaces as 404
  (`infra/iam/deploy-role.tf`), and add a `head-object` preflight before any
  mutation in `scripts/deploy.sh`. Rule: a cross-account 403 on a fetch is a
  missing object until proven otherwise — check the lifecycle policy and list
  the prefix before you touch IAM.

## Never deploy from an artifact bucket you do not own

**A deploy that reads its artifact from another account's bucket inherits
  that account's lifecycle rules, and a lifecycle rule is a scheduled
  deletion** (2026-09-14, same incident): `acme-build-artifacts` expired
  `api/` objects after 30 days to control cost, so any release older than 30
  days became un-redeployable and un-rollbackable at once, and the failure
  arrived mid-deploy — `update-function-configuration` had already run when
  `s3 cp` failed, leaving the function's `RELEASE` variable pointing at code
  that was never uploaded. Fix: promotion copies the artifact into a
  prod-owned bucket with no expiration (`acme-prod-release-artifacts`,
  `infra/s3/release-artifacts.tf`; `scripts/promote.sh`), and
  `scripts/deploy.sh` reads only from that bucket, verifies the object
  exists, then updates code BEFORE configuration. Rule: the deploying
  account owns every byte it deploys, and no mutation runs until every
  input is confirmed present.
