import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_tasks_crud_and_xp(client: AsyncClient, auth_headers: dict):
    # Create Task
    res = await client.post(
        "/tasks",
        json={"title": "Setup FastAPI", "description": "Configure routers"},
        headers=auth_headers,
    )
    assert res.status_code == 201
    task = res.json()
    assert task["title"] == "Setup FastAPI"
    assert task["status"] == "backlog"
    assert task["position"] == 0
    task_id = task["id"]

    # List Tasks
    list_res = await client.get("/tasks", headers=auth_headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    # Update Task to DOING
    update_res = await client.patch(
        f"/tasks/{task_id}",
        json={"status": "doing"},
        headers=auth_headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "doing"

    # Mark as DONE (awards 10 XP)
    done_res = await client.patch(
        f"/tasks/{task_id}",
        json={"status": "done"},
        headers=auth_headers,
    )
    assert done_res.status_code == 200
    assert done_res.json()["status"] == "done"
    assert done_res.json()["completed_at"] is not None

    # Check Dashboard for 10 XP
    dash_res = await client.get("/dashboard", headers=auth_headers)
    assert dash_res.status_code == 200
    stats = dash_res.json()["stats"]
    assert stats["xp_total"] == 10
    assert stats["streak"] == 1

    # Delete Task
    del_res = await client.delete(f"/tasks/{task_id}", headers=auth_headers)
    assert del_res.status_code == 204


@pytest.mark.asyncio
async def test_reorder_tasks(client: AsyncClient, auth_headers: dict):
    t1 = (await client.post("/tasks", json={"title": "Task 1"}, headers=auth_headers)).json()
    t2 = (await client.post("/tasks", json={"title": "Task 2"}, headers=auth_headers)).json()

    reorder_res = await client.post(
        "/tasks/reorder/today",
        json=[t2["id"], t1["id"]],
        headers=auth_headers,
    )
    assert reorder_res.status_code == 200
    reordered = reorder_res.json()
    assert len(reordered) == 2
    assert reordered[0]["id"] == t2["id"]
    assert reordered[0]["status"] == "today"
    assert reordered[0]["position"] == 0
    assert reordered[1]["id"] == t1["id"]
    assert reordered[1]["status"] == "today"
    assert reordered[1]["position"] == 1
