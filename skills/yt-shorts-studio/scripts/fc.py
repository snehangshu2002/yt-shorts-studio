"""FilmCraft live-bridge helper (module + CLI).

The FilmCraft MCP server can run headless (`filmcraft-cli mcp --demo`): edits then live in an
invisible engine and never show in the user's window. Live editing needs the app started with
a control port + token, and the CLI/MCP pointed at it with --bridge.

  python fc.py setup [--port 47321]   create the token + launcher in ~/.filmcraft_bridge/, point
                                      Claude Code's `filmcraft` MCP entry (~/.claude.json, backed up)
                                      at the bridge if Claude Code is installed, and print the MCP
                                      config snippet for other agents (Codex, Antigravity/Gemini...)
  python fc.py launch [project.fcproj] start the app with the control server if it isn't listening
  python fc.py status                 is the bridge reachable? which project is open?
  python fc.py exec <id> '<json>'     run one command in the live app, print JSON
  python fc.py run <script.jsonl>     run many commands (stops at the first failure)
  python fc.py export <sequence_id> <out.mp4> <width> <height> <fps> [--kbps 20000] [--scale 1]

After `setup`, the user must close any FilmCraft window that was opened normally, then you run
`launch`; an agent's FilmCraft MCP tools switch to the live app only after that MCP server is
restarted/reconnected (Claude Code: /mcp -> Reconnect). The CLI bridge (exec/run) works
immediately in any agent, so the skill's scripts never depend on the MCP server.
"""
import json, os, secrets, shutil, socket, subprocess, sys

HOME = os.path.expanduser("~")
CFG = os.path.join(HOME, ".claude.json")
STATE_DIR = os.path.join(HOME, ".filmcraft_bridge")
DEFAULT_PORT = 47321
CANDIDATES = [r"C:\Program Files\ArtCraft\FilmCraft", "/Applications/FilmCraft.app/Contents/MacOS", "/usr/bin", "/usr/local/bin"]


def find_exe(name):
    home = os.environ.get("FILMCRAFT_HOME")
    for d in ([home] if home else []) + CANDIDATES:
        for n in (name + ".exe", name):
            p = os.path.join(d, n)
            if os.path.isfile(p):
                return p
    return shutil.which(name)


def _cfg():
    try:
        return json.load(open(CFG, encoding="utf-8"))
    except Exception:
        return {}


def bridge_settings():
    """(port, token): env vars, then ~/.filmcraft_bridge/, then Claude Code's MCP config."""
    port = int(os.environ.get("FILMCRAFT_CONTROL_PORT") or 0) or None
    token = os.environ.get("FILMCRAFT_CONTROL_TOKEN")
    tp, pp = os.path.join(STATE_DIR, "token"), os.path.join(STATE_DIR, "port")
    if not token and os.path.exists(tp):
        token = open(tp).read().strip()
    if not port and os.path.exists(pp):
        port = int(open(pp).read().strip())
    e = _cfg().get("mcpServers", {}).get("filmcraft", {})
    if not token:
        token = e.get("env", {}).get("FILMCRAFT_CONTROL_TOKEN")
    args = e.get("args", [])
    if not port and "--bridge" in args:
        try:
            port = int(args[args.index("--bridge") + 1].rsplit(":", 1)[1])
        except Exception:
            pass
    return port or DEFAULT_PORT, token


def listening(port):
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def _cli(args, timeout=600):
    port, token = bridge_settings()
    env = dict(os.environ, FILMCRAFT_CONTROL_TOKEN=token or "")
    r = subprocess.run([find_exe("filmcraft-cli"), "--bridge", f"127.0.0.1:{port}", "--compact"] + args,
                       capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL, timeout=timeout)
    return r


def exec_cmd(cmd_id, params=None, timeout=600):
    r = _cli(["exec", cmd_id, json.dumps(params or {})], timeout)
    if r.returncode != 0:
        raise RuntimeError(f"{cmd_id} failed: {r.stdout.strip()} {r.stderr.strip()}")
    out = r.stdout.strip()
    return json.loads(out) if out and out != "null" else None


def run_script(path, timeout=1800):
    """Run a JSONL command script. Stops at the first failing line (on purpose: commands that
    omit "clip" act on the graphic made by the previous line, so continuing after a failure
    would restyle the wrong clip). Returns the parsed result lines."""
    r = _cli(["run", path], timeout)
    res = [json.loads(l) for l in r.stdout.splitlines() if l.strip().startswith("{")]
    bad = [x for x in res if not x.get("ok")]
    if r.returncode != 0 or bad:
        raise RuntimeError(f"run {path}: {len(res)} lines, first failure: {bad[:1] or r.stderr.strip()}")
    return res


def setup(port=DEFAULT_PORT):
    cur_port, token = bridge_settings()
    if token:
        port = cur_port
    token = token or secrets.token_hex(32)
    os.makedirs(STATE_DIR, exist_ok=True)
    open(os.path.join(STATE_DIR, "token"), "w").write(token)
    open(os.path.join(STATE_DIR, "port"), "w").write(str(port))
    cli = find_exe("filmcraft-cli")
    if os.path.exists(CFG):   # Claude Code installed: point its MCP entry at the bridge
        cfg = _cfg()
        e = cfg.setdefault("mcpServers", {}).get("filmcraft", {})
        if "--bridge" in e.get("args", []) and e.get("env", {}).get("FILMCRAFT_CONTROL_TOKEN") == token:
            print(f"Claude Code: 'filmcraft' MCP already bridges to port {port}")
        else:
            shutil.copy2(CFG, CFG + ".bak-filmcraft")
            cfg["mcpServers"]["filmcraft"] = {"type": "stdio", "command": cli,
                                              "args": ["mcp", "--bridge", f"127.0.0.1:{port}"],
                                              "env": {"FILMCRAFT_CONTROL_TOKEN": token}}
            json.dump(cfg, open(CFG, "w", encoding="utf-8"), indent=2)
            print(f"Claude Code: 'filmcraft' MCP now bridges to 127.0.0.1:{port} (backup: {CFG}.bak-filmcraft)")
    print("Other agents: add this MCP server (token is in ~/.filmcraft_bridge/token):")
    print(f'  command: "{cli}"  args: ["mcp", "--bridge", "127.0.0.1:{port}"]  env: FILMCRAFT_CONTROL_TOKEN=<token>')
    print("  Codex (~/.codex/config.toml):  [mcp_servers.filmcraft] command = ..., args = [...], env = { FILMCRAFT_CONTROL_TOKEN = \"...\" }")
    app = find_exe("filmcraft")
    if os.name == "nt":
        lines = ["@echo off", f"set FILMCRAFT_CONTROL_TOKEN={token}",
                 f'start "" "{app}" --control {port} %*']
        open(os.path.join(STATE_DIR, "FilmCraft_Live.cmd"), "w", newline="\r\n").write("\n".join(lines) + "\n")
        print(f"launcher: {os.path.join(STATE_DIR, 'FilmCraft_Live.cmd')}")
    else:
        p = os.path.join(STATE_DIR, "filmcraft_live.sh")
        open(p, "w").write(f'#!/bin/sh\nFILMCRAFT_CONTROL_TOKEN={token} exec "{app}" --control {port} "$@"\n')
        os.chmod(p, 0o700)
        print(f"launcher: {p}")


def launch(project=None):
    port, token = bridge_settings()
    if listening(port):
        print(f"FilmCraft control server already listening on {port}")
        return
    if not token:
        sys.exit("no token: run `fc.py setup` first")
    args = [find_exe("filmcraft"), "--control", str(port)] + ([os.path.abspath(project)] if project else [])
    env = dict(os.environ, FILMCRAFT_CONTROL_TOKEN=token)
    kw = {"creationflags": 0x00000008 | 0x00000200} if os.name == "nt" else {"start_new_session": True}
    subprocess.Popen(args, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)
    import time
    for _ in range(60):
        if listening(port):
            print(f"FilmCraft started with control on {port}")
            return
        time.sleep(0.5)
    sys.exit("FilmCraft did not open its control port; is another FilmCraft window already open?")


def status():
    port, token = bridge_settings()
    if not listening(port):
        print(json.dumps({"bridge": False, "port": port, "reason": "nothing listening (app closed or not started with --control)"}))
        return False
    r = _cli(["inspect", "project"], 60)
    if r.returncode != 0:
        print(json.dumps({"bridge": False, "port": port, "reason": (r.stdout + r.stderr).strip()[:300]}))
        return False
    p = json.loads(r.stdout)
    print(json.dumps({"bridge": True, "port": port, "project": p.get("name"), "path": p.get("path"),
                      "activeSequence": p.get("activeSequence")}))
    return True


def export(seq, out, w, h, fps, kbps=20000, scale=1.0):
    return exec_cmd("file.exportMedia", {"path": os.path.abspath(out), "format": "h264", "sequence": int(seq),
                                         "range": "entire", "width": int(w), "height": int(h), "fps": float(fps),
                                         "scale": scale, "h264Profile": "high", "bitrateMode": "vbr2Pass",
                                         "bitrateKbps": int(kbps), "audioCodec": "aac", "wait": True}, timeout=7200)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    cmd = a[0]
    if cmd == "setup":
        setup(int(a[a.index("--port") + 1]) if "--port" in a else DEFAULT_PORT)
    elif cmd == "launch":
        launch(a[1] if len(a) > 1 else None)
    elif cmd == "status":
        sys.exit(0 if status() else 1)
    elif cmd == "exec":
        print(json.dumps(exec_cmd(a[1], json.loads(a[2]) if len(a) > 2 else {})))
    elif cmd == "run":
        print(f"{len(run_script(a[1]))} commands ok")
    elif cmd == "export":
        kb = int(a[a.index("--kbps") + 1]) if "--kbps" in a else 20000
        sc = float(a[a.index("--scale") + 1]) if "--scale" in a else 1.0
        print(json.dumps(export(a[1], a[2], a[3], a[4], a[5], kb, sc)))
    else:
        sys.exit(__doc__)
