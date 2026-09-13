Class 1:
- One GPU instance with two vLLM pods.
- Text/vision capability routing.
- Gateway, router, and Superlinked fallback.
- Fake-worker tests and basic real-worker smoke tests.
- Supporting components installed/configured.
Planned for tomorrow:
- Real concurrency/load testing.
- Disaggregated prefill/decode behavior.
- KV sharing, transfer, and eviction.
- Scaling and resizing under load.
- Cluster observability and dashboards.


We used one Lambda GPU machine running a single-node K3s Kubernetes cluster. Kubernetes Deployments managed two vLLM pods, configured for text and vision, while HAMi’s scheduler and device plugin enabled them to share the physical NVIDIA GPU through memory and compute allocations. Each vLLM instance had its own model weights, scheduler and GPU KV cache. Our custom Python gateway handled tenant admission, and our router selected workers by capability, health and KV headroom. Kubernetes Services provided internal addresses; hostPort and NodePort mappings exposed endpoints, and our Mac-based test runner reached the workers through SSH tunnels, without an ingress/load-balancer hop. Requests waited in the client thread pool or vLLM scheduler; a separate gateway queue wasn’t implemented. Local capacity failures could trigger Superlinked API fallback. We also deployed a Mooncake-named Python service for KV-handoff metadata, with real Mooncake tensor transfer reserved for later work. KEDA and scaling rules were installed for metric-driven replica scaling, while Prometheus/Grafana observability was planned. Our completed experiment demonstrated text-worker saturation and successful external fallback—not distributed KV transfer or autoscaling.

The components answer different questions:
Component	Its job
Kubernetes/K3s	Keep the declared application pods running
HAMi	Allocate shared GPU resources to pods
Gateway	Decide whether a tenant’s request may enter
Router	Choose an eligible inference worker
vLLM	Schedule and execute inference; manage local KV cache
Mooncake	Intended distributed KV storage/transfer layer; metadata stand-in here
KEDA	Request more or fewer worker replicas from metrics
Superlinked	Serve eligible fallback requests
Prometheus/Grafana	Collect and visualize metrics; planned for the follow-up