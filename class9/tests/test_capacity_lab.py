import json

from gateway.types import Request
from scripts.capacity_lab import LoadWorker, reached_target


def test_load_worker_preserves_load(monkeypatch):
    worker = LoadWorker('test', 'http://unused', model='test')
    captured = {}
    def post(path, payload):
        captured.update(payload)
        return json.dumps({'choices': []})
    monkeypatch.setattr(worker, '_post', post)
    req = Request('id', 0, 1, 32, 1024, None, 60, 'tenant', prompt='Long prompt')
    worker.enqueue(req)
    assert captured['max_tokens'] == 1024
    assert captured['ignore_eos'] is True
    assert captured['messages'][0]['content'] == 'Long prompt'


def test_overflow_requires_success_and_capacity_reason():
    event = dict(status=200, via='overflow', local_status=503, reason='kv_free')
    assert reached_target('overflow', [event])
    assert not reached_target('overflow', [dict(event, status=502)])
    assert not reached_target('overflow', [dict(event, reason='no_eligible_pod')])
    assert not reached_target('saturation', [event])


def test_503_requires_real_capacity_for_saturation_mode():
    event = dict(status=503, via='local', reason='kv_free')
    assert reached_target('saturation', [event])
    assert not reached_target('saturation', [dict(event, reason='no_eligible_pod')])


def test_worker_error_is_not_a_completion(monkeypatch):
    import pytest
    worker = LoadWorker('test', 'http://unused', model='test')
    monkeypatch.setattr(worker, '_post', lambda *a: json.dumps({'error': {'message': 'model missing', 'code': 404}}))
    req = Request('id', 0, 1, 32, 16, None, 60, 'tenant')
    with pytest.raises(ValueError, match='model missing'):
        worker.enqueue(req)
