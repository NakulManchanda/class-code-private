# Class 9

Gateway + Router. Run these in order.

Do not `source .env` until Step 19.

## Laptop

### Step 1

```
cd class-code/class9
```

### Step 2

```
python3 -m venv .venv
```

### Step 3

```
source .venv/bin/activate
```

### Step 4

```
pip install -U pip && pip install -r requirements.txt
```

### Step 5

```
pytest tests/
```

Expect green. `test_vllm_worker` skipped.

### Step 6

Same terminal.

```
python -m fakeworker.run --list
```

### Step 7

```
python -m fakeworker.run --behavior fleet-soak
```

### Step 8

```
python -m fakeworker.run --behavior tenant-429-stays
```

### Step 9

```
python -m fakeworker.run --behavior overflow-on-503
```

---

## Lambda cluster

### Step 10

Mac terminal. Still in `class-code/class9`.

```
bash setup/sync_to_lambda.sh
```

### Step 11

Same Mac terminal.

```
bash setup/ssh.sh
```

### Step 12

Same terminal. Your prompt should look like `ubuntu@…:~/class9$`. Do not open a new Mac tab.

```
bash setup/lambda_setup.sh
```

### Step 13

Same GPU-box terminal.

```
bash setup/lambda_cluster.sh
```

### Step 14

Same GPU-box terminal.

```
kubectl get deploy,svc,scaledobject
```

### Step 15

Same GPU-box terminal.

```
bash setup/smoke_sliced.sh
```

---

## Send traffic

Need a `.env` first.

### Step 16

Same GPU-box terminal, or a new Mac terminal.

```
cp .env.example .env
```

Fill hosts and keys in `.env`, then continue.

### Step 17

New Mac terminal (or stay on the GPU box if this laptop cannot reach `:8000` / `:8001`).

```
cd class-code/class9
```

### Step 18

```
source .venv/bin/activate
```

### Step 19

```
set -a && source .env && set +a
```

### Step 20

```
python app.py
```

Wait for the prompt. Type **one line**, then wait for `ROUTE` and `TEXT`.

### Step 21

```
text Write one sentence about a GPU.
```

### Step 22

```
vision What color is this?
```

### Step 23

```
audio Transcribe: hello from class 9.
```

### Step 24

```
quit
```

### Step 25

```
tail -n 5 traces/requests.jsonl
```
