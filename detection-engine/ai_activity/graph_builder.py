"""Build execution graphs and spawn-path summaries for AI sessions."""

from __future__ import annotations

from ai_activity.models import (
    AISession,
    ExecutionGraph,
    GraphEdge,
    GraphNode,
)


def build_execution_graph(session: AISession) -> ExecutionGraph:
    """Materialize spawn + tool + notable network edges for UI."""
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    seen: set[str] = set()

    # Prefer ancestry-ordered walk from root
    order = _walk_order(session)
    for process_id in order:
        if len(nodes) >= session.max_graph_nodes:
            break
        node = session.processes.get(process_id)
        if node is None:
            continue
        label = node.name or process_id
        if node.tool_class:
            label = f"{node.tool_class}:{node.name}"
        nodes.append(
            GraphNode(
                id=process_id,
                label=label,
                kind="process",
                role=node.role,
                meta={
                    "pid": node.pid,
                    "tool_class": node.tool_class,
                    "terminated": node.terminated,
                },
            )
        )
        seen.add(process_id)
        if node.parent_process_id and node.parent_process_id in session.processes:
            edges.append(
                GraphEdge(
                    source=node.parent_process_id,
                    target=process_id,
                    relation="spawns",
                )
            )

    # Tool highlight edges (root → tool) for compact UI path
    for tool in session.tools[-50:]:
        if tool.process_id in seen and session.root_process_id in seen:
            edges.append(
                GraphEdge(
                    source=session.root_process_id,
                    target=tool.process_id,
                    relation="uses_tool",
                    meta={"tool_class": tool.tool_class},
                )
            )

    # Network nodes for external domains (collapsed)
    for domain in session.external_domains[:30]:
        nid = f"net:{domain}"
        if nid in seen:
            continue
        nodes.append(
            GraphNode(
                id=nid,
                label=domain,
                kind="network",
                role="network",
                meta={},
            )
        )
        seen.add(nid)
        # Link from most recent process that talked to this domain
        src = session.root_process_id
        for net in reversed(session.networks):
            if net.domain == domain or net.remote_addr == domain:
                src = net.process_id
                break
        if src in session.processes or src == session.root_process_id:
            edges.append(GraphEdge(source=src, target=nid, relation="network"))

    return ExecutionGraph(nodes=nodes, edges=edges)


def execution_path_summary(session: AISession, *, limit: int = 12) -> list[str]:
    """Human-readable chain: Cursor → Renderer → bash → pip → …"""
    path: list[str] = []
    # Start at root
    root = session.processes.get(session.root_process_id)
    if root:
        path.append(root.name or session.app_name)

    # Prefer deepest recent tool chain via last tools
    for tool in session.tools[-limit:]:
        label = tool.name or tool.tool_class
        if label and (not path or path[-1] != label):
            path.append(label)

    # Append last notable domain
    if session.external_domains:
        path.append(session.external_domains[-1])

    return path[: limit + 2]


def _walk_order(session: AISession) -> list[str]:
    order: list[str] = []
    seen: set[str] = set()

    def dfs(pid: str) -> None:
        if pid in seen:
            return
        seen.add(pid)
        order.append(pid)
        node = session.processes.get(pid)
        if not node:
            return
        for child in node.children:
            dfs(child)

    if session.root_process_id in session.processes:
        dfs(session.root_process_id)
    # Orphans in session (should be rare)
    for pid in session.processes:
        if pid not in seen:
            dfs(pid)
    return order


def spawn_tree_dict(session: AISession) -> dict:
    """Nested dict tree from root for API consumers."""

    def build(process_id: str) -> dict:
        node = session.processes.get(process_id)
        if node is None:
            return {"process_id": process_id}
        return {
            "process_id": process_id,
            "pid": node.pid,
            "name": node.name,
            "role": node.role,
            "tool_class": node.tool_class,
            "cmdline": node.cmdline,
            "terminated": node.terminated,
            "children": [build(c) for c in node.children if c in session.processes],
        }

    if session.root_process_id not in session.processes:
        return {}
    return build(session.root_process_id)
