# Class 9 transcript: questions, Q&A and scenarios

Source: `scripts/class_transcript`, all 292 lines, timestamps 11:32–13:57.
Audited in four contiguous chunks: lines 1–74, 75–148, 149–222 and 223–292.
This is a question/scenario index only, without answers or technical elaboration.

Labels:
- **Instructor**: an explicit question or exercise posed by the instructor.
- **Student**: a student question or clarification, with attribution inferred from conversational turns; the transcript has no reliable speaker labels.
- **Scenario**: an instructor-described situation or design choice, rewritten as a study question; not necessarily asked verbatim.
- **Logistics**: course, setup or classroom clarification.

Wording is normalized, repeated continuations are consolidated, and timestamps
refer to the source transcript (not elapsed video time). Unclear terms remain
flagged rather than silently resolved. Statements made in the transcript are
not independently verified here. In particular, this index does not endorse
its interpretations of status codes, tools, company deployments or acquisitions.
Greetings, screen-sharing checks and unrelated background speech are excluded.
Substantive setup questions and comprehension checks are retained for completeness.

## A. Preparation, production incidents and the project · 11:32–11:46

- **Q001 · 11:32–11:33 · Logistics:** Did students review the material posted the previous week?
- **Q002 · 11:35 · Scenario:** If reading all the research papers takes too long, what minimum parts should students study first?
- **Q003 · 11:35 · Scenario:** How much detail from the original vLLM paper remains useful when the implementation has changed?
- **Q004 · 11:36–11:37 · Scenario:** How should students use the queueing/system-design books without reading them cover to cover?
- **Q005 · 11:37 · Scenario:** How can classical systems techniques provide alternatives to a supposedly new LLM technique?
- **Q006 · 11:38 · Scenario:** How do conventional systems handle rate limiting and scaling, and which lessons transfer to inference?
- **Q007 · 11:38–11:39 · Scenario:** How can incorrect capacity signals break a distributed system? [Referenced postmortem not identified by name.]
- **Q008 · 11:39–11:40 · Scenario:** Given a production incident, how do you quickly identify the layer where the problem originated?
- **Q009 · 11:40 · Scenario:** How does platform work differ between building a new cluster and maintaining an existing one?
- **Q010 · 11:41 · Instructor:** Why did the referenced interface suffer degraded performance from a backlog of requests? [Service name transcribed as “Tally”; uncertain.]
- **Q011 · 11:41–11:42 · Scenario:** Does an incident belong to admission control, routing or queueing, and when should vLLM optimization enter the investigation?
- **Q012 · 11:42–11:44 · Scenario:** How do the homework production-incident reproductions progress from fake instances to a real GPU cluster with costs?
- **Q013 · 11:44 · Logistics:** Does everyone understand the final project and what they should demonstrate?
- **Q014 · 11:44–11:45 · Scenario:** After building the cluster and adding observability, how will changing arrival and eviction priorities become further experiments?
- **Q015 · 11:45–11:46 · Scenario:** How can a dashboard distinguish load-balancer, gateway and model performance?

## B. Architecture, models and access · 11:46–12:02

- **Q016 · 11:46–11:47 · Scenario:** What API-key spending limit should students set for the Superlinked experiment?
- **Q017 · 11:47 · Scenario:** Where should excess requests go when the two local vLLM instances cannot handle them?
- **Q018 · 11:48 · Scenario:** Can another provider be used instead of Lambda, and how would its instance setup differ? [Provider transcribed as “model”; likely a name, not certain.]
- **Q019 · 11:48–11:49 · Scenario:** How can one GPU instance be treated as a small cluster for this lab?
- **Q020 · 11:51 · Student:** Are we using only Lambda today, or also the other service?
- **Q021 · 11:51–11:53 · Scenario:** What is the request path through app.py, gateway, router, pods and overflow.py?
- **Q022 · 11:53 · Scenario:** What happens when the router finds no container with capacity?
- **Q023 · 11:54 · Student:** Are both containers running on one Lambda instance?
- **Q024 · 11:54 · Student:** What runs on Superlinked—our containers or a model API?
- **Q025 · 11:54–11:55 · Scenario:** How should the router distinguish text, vision and an unsupported modality such as speech?
- **Q026 · 11:55 · Scenario:** When would you use a heterogeneous model setup versus several copies of a text model?
- **Q027 · 11:55 · Scenario:** How will Mooncake support KV management, eviction and sharing between pods in the follow-up lab?
- **Q028 · 11:56 · Logistics:** Where is the code for today's class?
- **Q029 · 11:56–11:57 · Student:** Can the material be explained through short scenarios, and can students use scenario-based notes to study?
- **Q030 · 11:57 · Scenario:** What should students do when they are falling behind or blocked on the material?
- **Q031 · 11:58–11:59 · Logistics:** How should the supplied SSH key be saved, and which machine login username should be used?
- **Q032 · 12:00 · Student:** Which GPU instance type and memory size should be selected?
- **Q033 · 12:00 · Scenario:** Why deliberately use a smaller instance that exposes concurrency problems instead of immediately buying a larger one?
- **Q034 · 12:00–12:01 · Student:** Do the supplied SSH credentials also provide Lambda console access, and is console access needed?
- **Q035 · 12:01 · Scenario:** Could two students or instructor and student interfere with each other on a shared instance; should a separate instance be created?

## C. Components, metrics and local testing · 12:03–12:22

- **Q036 · 12:03–12:04 · Scenario:** What should a fake GPU/worker simulate when testing admission and routing policies locally?
- **Q037 · 12:04 · Scenario:** What token-rate constraint is the gateway's admission layer checking?
- **Q038 · 12:04–12:05 · Scenario:** Which cluster-level metrics are needed beyond vLLM throughput, decode/prefill speed and TTFT?
- **Q039 · 12:05 · Scenario:** How should total requests, router sheds, picks, tokens in flight, KV headroom, evictions and transfers appear in the second dashboard?
- **Q040 · 12:05 · Scenario:** How is the previous class's queue intended to fit into the gateway? [Transcript claim; implementation not audited here.]
- **Q041 · 12:06 · Scenario:** How do health, active requests and snapshot freshness affect whether a pod can be selected?
- **Q042 · 12:06–12:08 · Scenario:** Where are gateway/model configurations and per-slice memory settings changed, and how would later dashboard controls relate to them?
- **Q043 · 12:07–12:09 · Scenario:** What responsibilities are assigned to HAMi, Mooncake and KEDA for slicing, cache management and replica scaling? [Tool names normalized from transcription.]
- **Q044 · 12:10 · Scenario:** What distinction does the instructor draw between tenant 429 and router 503?
- **Q045 · 12:11 · Scenario:** If both pods or the Lambda server go down, how can fallback prevent rejecting every request?
- **Q046 · 12:11–12:12 · Scenario:** What routing/scaling decisions belong in planner.py?
- **Q047 · 12:12 · Scenario:** What must a trace record to explain latency, timeout, status, reason and noisy-tenant behavior later?
- **Q048 · 12:13–12:14 · Scenario:** Which checks should pass on a fake cluster before moving to real GPUs?
- **Q049 · 12:15 · Scenario:** How does the sample app.py relate to a real RAG or agentic application's entry point?
- **Q050 · 12:16–12:17 · Student:** Do we need two replicas, or one setup containing two pods, and how does GPU memory constrain that layout? [Replica/pod wording is inconsistent in the transcript.]
- **Q051 · 12:17 · Scenario:** Why keep prefill and decode separable for the later disaggregation and KV exercises?
- **Q052 · 12:18–12:19 · Scenario:** Which behavior does the bind-capability test verify for text versus vision requests?
- **Q053 · 12:19–12:20 · Instructor:** Pick a fake-worker behavior, add a small print statement and inspect how the gateway and router handle it.
- **Q054 · 12:20–12:21 · Scenario:** Send 20 requests to a small fake fleet: how many complete, shed and overflow?
- **Q055 · 12:21 · Scenario:** How would you check whether overflow generated activity at the external provider? [The instructor's claim about fake-run API traffic is not verified here.]
- **Q056 · 12:21–12:22 · Scenario:** What does tenant-429-stays intend to demonstrate about noisy and quiet tenants? [The verbal interpretation of 200/429 is inconsistent.]

## D. Python and harness comprehension checks · 12:23–12:34

- **Q057 · 12:23–12:24 · Instructor:** What does `from __future__ import annotations` do?
- **Q058 · 12:24–12:25 · Instructor:** What does argparse do with command-line arguments?
- **Q059 · 12:25 · Instructor:** What does importing os let this program do?
- **Q060 · 12:25–12:26 · Scenario:** Why does cluster tooling need operating-system/file access, and what clock information does this harness need? [Clock/module explanation in the transcript is unclear.]
- **Q061 · 12:26–12:27 · Instructor:** What does redirecting output with contextlib do, and why save output instead of only printing it?
- **Q062 · 12:28–12:29 · Scenario:** Why represent the behavior result as a dataclass rather than writing the initialization manually?
- **Q063 · 12:29–12:30 · Scenario:** How do request priority, prompt tokens, maximum new tokens and the lab label define a test request?
- **Q064 · 12:30 · Scenario:** How would traces distinguish experimental requests from production requests?
- **Q065 · 12:31–12:32 · Instructor:** What does the fleet-construction section do, and how do prefill workers, decode workers and the shared KV bus fit together?
- **Q066 · 12:32–12:33 · Instructor:** What happens in fleet-soak when too many requests hit the system; what does it test and where can it fail?
- **Q067 · 12:33–12:34 · Instructor:** What should BehaviorResult report—pass/fail, completions, sheds, overflow attempts and overflow completions?
- **Q068 · 12:34–12:35 · Instructor:** Does everyone understand fleet behavior and the distinction between 429 and 503?

## E. Edge-case questions and exercises · 12:36–12:57

- **Q069 · 12:36–12:37 · Student:** If fleet-soak uses `for i in range(20)`, aren't the requests sent sequentially rather than concurrently? [The subsequent explanation uses both descriptions.]
- **Q070 · 12:37 · Scenario:** What does “soak” mean when applied to a fleet or cluster?
- **Q071 · 12:38–12:39 · Scenario:** If one decode pod is unhealthy and the other is saturated, should requests overflow or should the planner add decode capacity?
- **Q072 · 12:39 · Scenario:** Why should a decode-capacity problem not automatically allocate an extra prefill replica?
- **Q073 · 12:40 · Scenario:** Which edge cases should be retained in a reusable production cluster test harness?
- **Q074 · 12:40–12:41 · Instructor:** Who can explain the tenant-429-stays behavior?
- **Q075 · 12:41–12:42 · Scenario:** With two tenants and a tight token budget, how do you stop a noisy tenant consuming all capacity and harming the quiet tenant?
- **Q076 · 12:42–12:43 · Instructor:** What behavior does ignore-stale-pod test when pod A's snapshot is old and pod B's is current?
- **Q077 · 12:43–12:45 · Instructor:** For scale-decode-not-prefill, which file makes the decision and what exact behavior should the test demonstrate?
- **Q078 · 12:43–12:44 · Student:** Is this selective-scaling case specifically about disaggregated prefill and decode?
- **Q079 · 12:45–12:46 · Instructor:** Why print the abort-free-KV result, and under what condition should cache be freed?
- **Q080 · 12:46 · Scenario:** If a request is cancelled, how do you avoid wasting further decode work and retaining its KV allocation?
- **Q081 · 12:46–12:47 · Instructor:** What does prefix-sticky-saves-KV demonstrate compared with least-loaded routing?
- **Q082 · 12:47 · Scenario:** Should a request go to a less-loaded GPU without its prefix or a GPU where its prefix cache already exists?
- **Q083 · 12:48 · Instructor:** What should happen when both prefill and decode need more resources?
- **Q084 · 12:48–12:49 · Scenario:** Which tests exercise planner behavior, and which exercise overflow behavior?
- **Q085 · 12:49–12:50 · Scenario:** A small prompt fits the available slice but a large prompt does not: which request should proceed, and should the large one trigger overflow? [Introduced as the slicing/no-overflow behavior.]
- **Q086 · 12:50–12:51 · Student:** If small requests keep arriving, can a large request starve, and does aging eventually raise its priority?
- **Q087 · 12:51 · Scenario:** Should request aging be handled by admission or routing?
- **Q088 · 12:51–12:52 · Scenario:** How does overflow-on-503 test external fallback, and what latency/status/reason should be printed?
- **Q089 · 12:52 · Scenario:** How can the fake-worker scenarios be selected by full names or aliases?
- **Q090 · 12:52–12:53 · Logistics:** Does everyone understand the harness and steps completed before the real-GPU setup?
- **Q091 · 12:53–12:55 · Student:** Is router.py only for fake workers, or does the same code route actual traffic to Kubernetes/vLLM workers?
- **Q092 · 12:55–12:56 · Scenario:** How can generic gateway/router code be tested with a fake engine and later used with a real engine?
- **Q093 · 12:56–12:57 · Scenario:** What extra failures and timing uncertainties appear when moving from deterministic fake tests to real Lambda inference?

## F. Environment, fallback providers and extensions · 12:58–13:05

- **Q094 · 12:58 · Student:** Must .env.example be filled in before continuing, and which credentials belong there?
- **Q095 · 12:59 · Scenario:** Which local text/vision models and URLs can students change for later experiments?
- **Q096 · 12:59–13:01 · Scenario:** When would you use an external provider router rather than implement fallback routing yourself?
- **Q097 · 13:00–13:01 · Scenario:** How would you choose a default provider, cheapest route or preferred model?
- **Q098 · 13:01–13:02 · Scenario:** Where could additional guardrails or harness checks be added, and how do they differ from simple content restrictions?
- **Q099 · 13:03 · Student:** If we use OpenRouter, do we still need a separate Superlinked account, and who bills for usage?
- **Q100 · 13:04–13:05 · Scenario:** How could pickbackend.py select different fallback providers or cheaper versus more expensive models without rewriting the whole router?
- **Q101 · 13:05 · Scenario:** Could an agentic decision process be added to choose the backend?

## G. Installation failures and live troubleshooting · 13:06–13:34

- **Q102 · 13:06–13:08 · Scenario:** What should lambda_setup.sh verify about GPU visibility, memory, CUDA, Torch, vLLM and installed requirements?
- **Q103 · 13:08–13:09 · Scenario:** What can cause a HAMi/cluster installation to stall—pod creation, port setup, timeout or OOM—and when should students investigate?
- **Q104 · 13:09 · Scenario:** Where should configuration change if a student uses a smaller GPU?
- **Q105 · 13:10–13:12 · Scenario:** Which parts of setup are handled by K3s, Helm, HAMi and KEDA, and which placement decisions remain with the router?
- **Q106 · 13:12–13:13 · Scenario:** Which kubectl checks show running, pending and unhealthy pods?
- **Q107 · 13:13 · Scenario:** After a failed Helm/HAMi install, when might stale resources need cleanup before retrying?
- **Q108 · 13:13–13:15 · Scenario:** If the initial 50/50 GPU slices are insufficient under load, how should their allocation be reconsidered? [Reported memory units in the transcript are garbled.]
- **Q109 · 13:15–13:16 · Scenario:** Why inspect readiness and run troubleshooting commands in another SSH terminal while installation continues?
- **Q110 · 13:16 · Scenario:** What should happen if HAMi times out and the later KEDA install never runs?
- **Q111 · 13:16–13:18 · Scenario:** How do you interpret `kubectl get deploy,svc,scaledobject` output, including readiness, age, availability, addresses and ports?
- **Q112 · 13:18 · Scenario:** If the expected Kubernetes objects are absent, where should installation debugging begin?
- **Q113 · 13:19 · Student:** Mooncake deployment is taking too long and times out; how should it be diagnosed or retried?
- **Q114 · 13:19–13:20 · Scenario:** How will prefill and decode access the Mooncake store for cache reading and eviction?
- **Q115 · 13:21 · Student:** Setup prints only partial output / two models and nothing else; does that mean the system is ready? [Original symptom wording is incomplete.]
- **Q116 · 13:21–13:23 · Student:** How should “couldn't get server API” / an unhandled Kubernetes error be investigated?
- **Q117 · 13:23–13:24 · Scenario:** What if installation timed out before pods or a later kubeconfig step were created?
- **Q118 · 13:24–13:25 · Student:** How do we fix a missing or unconfigured kubeconfig, including when pods appear to be running?
- **Q119 · 13:25 · Student:** After setting kubeconfig, the smoke-slice command still fails—what should be checked next? [Error text is not preserved.]
- **Q120 · 13:26–13:27 · Student:** Why did we choose not to attach a filesystem when creating the Lambda instance?
- **Q121 · 13:28–13:31 · Student:** For “MountVolume.SetUp failed,” does the Kubernetes YAML need a corrected hostPath or mount configuration?
- **Q122 · 13:29–13:31 · Scenario:** Is the path referring to the node's filesystem or the container's filesystem, and are volume names and YAML structure correct? [Proposed fix is not conclusively documented.]
- **Q123 · 13:32–13:33 · Student:** After editing the configuration, do we need to resync the code?
- **Q124 · 13:33–13:34 · Student:** Should sync-to-Lambda run locally or inside the VM, and what if the student logged into the VM directly without syncing?
- **Q125 · 13:34 · Logistics:** Have the other students resolved their setup problems, or are there remaining blockers?

## H. Smoke tests, real traffic and interpretation · 13:35–13:46

- **Q126 · 13:35 · Student:** Are the prefill/decode components all vLLM pods, with Mooncake acting as the KV store?
- **Q127 · 13:35–13:36 · Student:** The README shows normal traffic; will we also do load testing?
- **Q128 · 13:36–13:37 · Scenario:** How do request-level and hardware-level concurrency experiments differ?
- **Q129 · 13:36–13:37 · Scenario:** Under enough traffic, when should decode grow by one, and when should both prefill and decode grow?
- **Q130 · 13:37 · Student:** Why is an environment file needed on the GPU machine?
- **Q131 · 13:37–13:38 · Student:** Is `python -m gateway.serve` the gateway implementation, and what responsibilities are in the gateway package?
- **Q132 · 13:38–13:39 · Student:** What does the gateway section under k8s-config configure?
- **Q133 · 13:39 · Scenario:** Where would you change replica counts, models, ports and KV-store location?
- **Q134 · 13:39–13:41 · Student:** What does the container command that installs requirements and starts gateway.serve actually do?
- **Q135 · 13:41 · Scenario:** How should students package their modified cluster implementation and example results as a final project?
- **Q136 · 13:42–13:44 · Scenario:** If the smoke request is overloaded or produces no local answer, how should admission, binding, placement, handoff, local status and final status be read?
- **Q137 · 13:44–13:45 · Instructor:** Show your final run: was the request served or rejected, what modality was it, and what result did you obtain?
- **Q138 · 13:44–13:45 · Scenario:** Could changing the prefill/decode allocation make a previously overflowing request fit locally? [The instructor mentions an approximate 5/95 split.]
- **Q139 · 13:45–13:46 · Scenario:** How do you interpret successful text/vision placement and a request with no KV handoff?
- **Q140 · 13:46 · Scenario:** If there is no matching audio model, why does the audio request go to the backup?

## I. Production tooling and closing choices · 13:46–13:57

- **Q141 · 13:46–13:47 · Scenario:** When might a multimodal capability be sent to an external API instead of hosted locally?
- **Q142 · 13:47 · Student:** Do production teams deploy Kubernetes/pods/vLLM directly like this, or is it abstracted by Ray or another framework?
- **Q143 · 13:47–13:48 · Scenario:** Where do training-oriented and serving-oriented frameworks fit in the instructor's comparison? [Claims about tool usage are transcript claims, not verified conclusions.]
- **Q144 · 13:48 · Scenario:** If a team already uses an orchestration tool, should it stay with it, and when does custom orchestration become too much to maintain?
- **Q145 · 13:48–13:49 · Scenario:** Which existing tool could replace handwritten routing, prefix-aware mapping or planner logic?
- **Q146 · 13:49–13:50 · Scenario:** What should you do if a framework does not support the model you need?
- **Q147 · 13:50 · Student:** Do large model providers still use Kubernetes underneath more sophisticated custom routers and gateways?
- **Q148 · 13:50–13:51 · Scenario:** When should you extend a general-purpose serving tool versus keep your own code with selected abstractions?
- **Q149 · 13:52 · Scenario:** Which external provider/backend options can replace the single Superlinked fallback?
- **Q150 · 13:53 · Scenario:** How does the handwritten endpoint-picking/gateway logic relate to Envoy, kgateway, agentgateway and GIE?
- **Q151 · 13:53–13:54 · Scenario:** How should KV-store/cache tooling be compared with lower-level transfer options such as RDMA/NVLink? [Several tool names are mistranscribed.]
- **Q152 · 13:54–13:55 · Scenario:** When would you choose HAMi, NVIDIA MIG, time slicing or another device scheduler?
- **Q153 · 13:55 · Scenario:** How should KEDA, Knative and a framework's own planner be compared for scaling?
- **Q154 · 13:55 · Scenario:** If Dynamo already provides planning, when would adding another scaler be useful?
- **Q155 · 13:56 · Scenario:** Can components be swapped plane by plane while preserving the overall serving architecture?
- **Q156 · 13:57 · Scenario:** How should tool choice change for different workloads, including agentic workloads?
- **Q157 · 13:57 · Student:** Should the Lambda instance be terminated after the class?

## Deferred detail / source limitations

- This list intentionally contains no reconstructed answers.
- The named fake-worker exercises appear mainly at 12:19–12:52; live troubleshooting mainly at 13:08–13:34; production-tool Q&A mainly at 13:47–13:57.
- Repeated questions are consolidated where they are the same conversational exchange; distinct prompts about the same concept remain separately numbered.
- Some on-screen commands, code and slide labels are absent from the transcript. The index does not invent their contents.
- The transcript ends during the closing remarks at 13:57. No subsequent class or promised follow-up is included.
