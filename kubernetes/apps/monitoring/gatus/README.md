# Gatus

Uptime monitoring and status page application for internal and external services.

## Overview

Gatus is deployed as a `StatefulSet` with persistent configuration storage. It uses an init container (`gatus-sidecar`) to automatically generate status page configurations from discovered Ingress resources and Services.

## Configuration

### Init Container (`gatus-sidecar`)

The `gatus-sidecar` init container runs only once during pod initialization to configure Gatus automatically:

- **`--enable-ingress`**: Auto-discovers and monitors Ingress endpoints
- **`--enable-service`**: Auto-discovers and monitors Service endpoints

**Important**: Init containers do NOT support `restartPolicy: Always`. This field is invalid and causes resource exhaustion if removed incorrectly (the kubelet may repeatedly attempt to restart the container). Init containers run once and must succeed before the main container starts.

### Storage

Gatus configuration is stored in a persistent PVC using OpenEBS Hostpath storage:
- Size: 5Gi
- Storage Class: openebs-hostpath
- Access Mode: ReadWriteOnce (StatefulSet requirement)

### Security Context

- **Pod-level**:
  - `runAsNonRoot: true` / `runAsUser: 65534` (nobody user)
  - `fsGroup: 65534` for PVC permissions
  
- **Container-level**:
  - Main container: `capabilities.add: ["NET_RAW"]` (required for ICMP ping)
  - Init container: `capabilities.drop: ["ALL"]` (minimal privileges)

### Resource Requests/Limits

- **Init container**: 10m CPU, 128Mi memory limit
- **Main container**: 100m CPU, 256Mi memory limit

These are conservative defaults suitable for most home deployments.

## Common Issues

### "failed to create pod sandbox: ... fork/exec /proc/self/exe: no space left on device"

This error appears when node system resources are exhausted, typically:

1. **Inotify limit exceeded** — Too many file watches (especially with `--enable-ingress`)
2. **Process/FD limits reached** — System ran out of process slots
3. **tmpfs/devtmpfs full** — `/dev` or similar tmpfs is full

**Solutions**:
- Check node disk space: `kubectl top nodes` and node conditions
- Verify kubelet can allocate new processes on the affected node
- If node k8s-4 is consistently problematic, exclude it with pod affinity:
  ```yaml
  pod:
    affinity:
      nodeAffinity:
        requiredDuringSchedulingIgnoredDuringExecution:
          nodeSelectorTerms:
            - matchExpressions:
                - key: kubernetes.io/hostname
                  operator: NotIn
                  values: ["k8s-4"]
  ```

### Pod stays in `Init:0/1`

The init container is still running. Check logs:
```bash
kubectl logs -n monitoring gatus-0 -c gatus-sidecar --previous
```

If the init container is hanging, it may be waiting on Ingress/Service discovery. Verify cluster networking is healthy.

### HelmRelease timeouts

The default Helm timeout (5m) may be insufficient if:
- Cluster is under load
- Node scheduling is slow
- PVC is taking time to bind

Increase the Helm timeout in `helmrelease.yaml`:
```yaml
install:
  remediation:
    retries: 3
  timeout: 10m  # Add this
upgrade:
  remediation:
    retries: 3
  timeout: 10m  # Add this
```

## Best Practices (aligned with home-ops)

1. **Image pinning**: Always use both tag AND digest
2. **Security**: All containers run as non-root with minimal capabilities
3. **Monitoring**: The app emits Prometheus metrics at `/metrics`
4. **Auto-reload**: Configured with `reloader.stakater.com/auto: "true"` to reload on ConfigMap/Secret changes
5. **Schema validation**: YAML includes proper `yaml-language-server` schema for IDE support

## Troubleshooting Commands

```bash
# Check pod status
kubectl get pods -n monitoring -l app.kubernetes.io/name=gatus

# View HelmRelease status
kubectl describe helmrelease gatus -n monitoring

# Check init container logs
kubectl logs -n monitoring gatus-0 -c gatus-sidecar

# View main container logs
kubectl logs -n monitoring gatus-0 -c app

# Check recent events
kubectl get events -n monitoring --sort-by='.lastTimestamp' | grep gatus

# Debug node issues
kubectl describe node k8s-4  # If pod scheduled there
kubectl debug node/k8s-4 -it --image=busybox
```

## Related Resources

- [Gatus GitHub](https://github.com/TwinProduction/gatus)
- [app-template Chart](https://github.com/bjw-s/helm-charts)
- [OpenEBS Documentation](https://openebs.io/)
