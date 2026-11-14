"""Removes the dead nodes write_graph_dsl leaves behind (Center session, 2026-11-07; author approved).

write_graph_dsl's delete_stale keeps every node it can reach over ANY pin link from a root. In a function graph the
previous version's nodes stay linked to the entry's parameter pins (SizeX, DeltaSeconds, Amount...), so every rewrite
left a whole old copy behind. By 2026-11-07, 89% of all nodes in /Game/Characters/Physis/Blueprints were dead, and
BP_PhysisHUD was 129 MB instead of 12. The scripts' write helpers call this after each write (op center:prune).

Live = reachable from a start over Exec OUTPUT links, plus everything feeding a reached node over non-Exec INPUT
links. Starts: a function graph's FunctionEntry. In any other graph: every node with an exec output and no exec input
(events, custom, input and bound events, macro tunnels), and every Timeline (AutoPlay runs with nothing wired in).
Never removed: comment boxes, entries, results (they define the signature), tunnels, events, timelines and starts.
Only nodes inside the graph are removed. The read_graph_dsl text must be identical before and after; it prints only
the live part, so any difference means something live went, and prune_graph reports it (same=False).
"""
import unreal


def _keep_classes():
    names = ('K2Node_FunctionEntry', 'K2Node_FunctionResult', 'K2Node_Tunnel', 'K2Node_Event', 'K2Node_CustomEvent',
             'K2Node_Timeline', 'EdGraphNode_Comment', 'K2Node_ComponentBoundEvent', 'K2Node_ActorBoundEvent')
    return tuple(c for c in (getattr(unreal, n, None) for n in names) if c)


def dead_nodes(graph):
    """(graph editor, dead nodes, node count) for one graph, by the rule above."""
    editor = unreal.BlueprintGraphEditor.get_graph_editor(graph)
    nodes = list(editor.list_all_nodes())
    keys = [n.get_path_name() for n in nodes]
    by_key = dict(zip(keys, nodes))
    timeline = getattr(unreal, 'K2Node_Timeline', ())
    exec_next, data_from, starts, entries = {}, {}, [], []
    for key, node in zip(keys, nodes):
        exec_in = exec_out = False
        nxt, src = set(), set()
        for pin in node.list_all_pins():
            is_exec = str(pin.get_pin_type_display_string()) == 'Exec'
            is_in = pin.get_pin_direction() == unreal.EdGraphPinDirection.EGPD_INPUT
            if is_in:
                exec_in = exec_in or is_exec
            else:
                exec_out = exec_out or is_exec
            for other in pin.list_connected_pins():
                owner = other.get_owning_node().get_path_name()
                if is_exec and not is_in:
                    nxt.add(owner)
                elif not is_exec and is_in:
                    src.add(owner)
        exec_next[key], data_from[key] = nxt, src
        if isinstance(node, unreal.K2Node_FunctionEntry):
            entries.append(key)
        elif (exec_out and not exec_in) or isinstance(node, timeline):
            starts.append(key)
    seen, stack = set(), list(entries if entries else starts)
    while stack:
        key = stack.pop()
        if key in seen or key not in by_key:
            continue
        seen.add(key)
        stack.extend(exec_next[key])
        stack.extend(data_from[key])
    keep, protected = seen | set(entries) | set(starts), _keep_classes()
    return editor, [by_key[k] for k in keys if k not in keep and not isinstance(by_key[k], protected)], len(nodes)


def prune_graph(graph):
    """Removes one graph's dead nodes. Returns {'graph', 'nodes', 'removed', 'same'}. same is False if the live DSL
    changed: then do not save, and reload the Blueprint from disk."""
    from editor_toolset.toolsets.blueprint import BlueprintTools
    editor, dead, total = dead_nodes(graph)
    row = {'graph': graph.get_name(), 'nodes': total, 'removed': len(dead), 'same': True}
    if dead:
        before = BlueprintTools.read_graph_dsl(graph)
        editor.remove_nodes(dead)
        row['same'] = before == BlueprintTools.read_graph_dsl(graph)
    return row


def prune_ref(ref):
    """ref is '<Blueprint object path>:<graph name>', as the write helpers pass to write_graph_dsl."""
    path, name = ref.rsplit(':', 1)
    blueprint = unreal.load_asset(path.split('.')[0])
    graph = next((g for g in unreal.BlueprintEditorLibrary.list_graphs(blueprint) if g.get_name() == name), None)
    if graph is None:
        raise ValueError('No graph %s in %s' % (name, path))
    return prune_graph(graph)
