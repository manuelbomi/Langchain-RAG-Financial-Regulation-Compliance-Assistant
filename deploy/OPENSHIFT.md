# Notes on Running This on OpenShift

The manifests under `deploy/k8s/` are plain Kubernetes and work on
OpenShift with a small number of adjustments, since OpenShift enforces a
stricter default security posture than vanilla Kubernetes.

## 1. Arbitrary UID assignment

OpenShift's default Security Context Constraint (`restricted-v2`) assigns
each pod a random UID at deploy time and rejects a hardcoded `runAsUser`.
The Dockerfile in this repo already avoids setting a fixed UID (it creates
`appuser` via `useradd --system`, then relies on the container runtime /
OpenShift to assign the actual runtime UID), and the image's writable
directories (`/app/.index`, `/app/.audit`) are group-writable under GID 0,
which is the standard OpenShift-compatible pattern. If you build your own
variant of this image, keep that pattern: never assume the container runs
as the UID baked into the image.

## 2. Routes instead of Ingress

Replace (or supplement) `deploy/k8s/service.yaml` usage with an OpenShift
`Route`:

```bash
oc expose service/compliance-copilot --port=80
```

or apply a `Route` manifest pointing at the `compliance-copilot` Service
defined in `deploy/k8s/service.yaml`.

## 3. ImageStreams (optional)

If your OpenShift cluster's build pipeline uses ImageStreams rather than
pulling directly from an external registry, tag the image built from this
repo's `Dockerfile` into an ImageStream and reference that in the
Deployment's `image:` field instead of `compliance-copilot:local`.

## 4. Secrets

`deploy/k8s/secret.yaml.example` works unmodified on OpenShift. If your
organization uses OpenShift's built-in secret management or an external
secrets operator, wire that up instead of committing a filled-in Secret
manifest anywhere.

## 5. Security Context Constraints (SCC)

The Deployment's `securityContext` (non-root, no privilege escalation, all
Linux capabilities dropped) is intentionally compatible with OpenShift's
`restricted-v2` SCC out of the box -- no custom SCC should be required for
this workload.
