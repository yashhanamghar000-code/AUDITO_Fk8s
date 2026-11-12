"""Router tests: authorization scoping, history handling and error mapping."""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from add_ai_core.entities.chat import ChatAnswer
from app.api.dependencies import get_container, get_current_user
from app.clients.llm_client import LlmServiceError
from app.main import app


class FakeHistory:
    """Behaves like the data-service: everything is keyed by the authenticated user id."""

    def __init__(self):
        self.files = {1: [{"id": "10", "status": "indexed"}, {"id": "11", "status": "processing"}],
                      2: [{"id": "20", "status": "indexed"}]}
        self.messages = {(1, "shared-session"): [{"sender": "user", "text": "alice secret question"},
                                                  {"sender": "bot", "text": "alice secret answer"}]}
        self.saved = []

    def list_files_for_user(self, user_id):
        return self.files.get(user_id, [])

    def get_chat_history(self, user_id, session_id):
        return self.messages.get((user_id, session_id), [])

    def save_chat_turn(self, user_id, session_id, query, response):
        self.saved.append((user_id, session_id, query, response))


class FakeWorkflow:
    def __init__(self):
        self.kwargs, self.error = None, None

    def run(self, **kwargs):
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return ChatAnswer(response_text="ok")


@pytest.fixture
def env():
    history, workflow = FakeHistory(), FakeWorkflow()
    container = SimpleNamespace(history_service=history, chat_workflow_service=workflow)
    user = {"id": 1}
    app.dependency_overrides[get_container] = lambda: container
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=user["id"], name="u", email="u@x")
    yield SimpleNamespace(client=TestClient(app), history=history, workflow=workflow, user=user)
    app.dependency_overrides.clear()


def post(env, **form):
    data = {"query": "q", "session_id": "shared-session", **form}
    return env.client.post("/api/chat", data=data)


def test_history_is_passed_to_the_workflow(env):
    assert post(env).status_code == 200
    assert env.workflow.kwargs["chat_history"] == [("user", "alice secret question"), ("assistant", "alice secret answer")]


def test_other_users_history_for_same_session_id_is_never_loaded(env):
    env.user["id"] = 2                                 # bob uses alice's session id
    assert post(env).status_code == 200
    assert env.workflow.kwargs["chat_history"] == []   # nothing of alice's leaks into bob's prompt
    assert env.workflow.kwargs["user_id"] == "2"


def test_cannot_select_another_users_file(env):
    r = post(env, file_ids="20")                      # file 20 belongs to user 2
    assert r.status_code == 404 and env.workflow.kwargs is None


def test_only_indexed_files_can_be_selected(env):
    assert post(env, file_ids="11").status_code == 404   # still processing
    assert post(env, file_ids="10").status_code == 200
    assert env.workflow.kwargs["selected_file_ids"] == ["10"]


def test_no_indexed_documents_is_404(env):
    env.user["id"] = 99
    assert post(env).status_code == 404


def test_successful_turn_is_saved_for_the_authenticated_user_only(env):
    post(env)
    assert env.history.saved == [(1, "shared-session", "q", "ok")]


@pytest.mark.parametrize("status", [429, 503, 504, 422])
def test_llm_errors_are_mapped_with_their_safe_message(env, status):
    env.workflow.error = LlmServiceError(status, "Friendly message.", "cat")
    r = post(env)
    assert r.status_code == status and r.json()["detail"] == "Friendly message."


def test_unexpected_errors_do_not_leak_internals(env):
    env.workflow.error = RuntimeError("connect to http://data-service:8007 failed key=sk-secret-123")
    r = post(env)
    assert r.status_code == 500
    assert "data-service" not in r.text and "sk-secret" not in r.text
    assert "Something went wrong" in r.json()["detail"]


def test_chat_requires_authentication():
    app.dependency_overrides.clear()
    r = TestClient(app).post("/api/chat", data={"query": "q", "session_id": "s"})
    assert r.status_code in (401, 403)
