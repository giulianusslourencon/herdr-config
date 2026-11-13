#!/usr/bin/env python3
"""Leitura do Espírito da Máquina: consumo do computador, em JSON, para os mods do Tomo.

  {"cpu": 23.4, "cores": 8, "load": [1.9, 1.4, 0.6],
   "mem": {"used": 8.1e9, "total": 1.6e10}, "swap": {...}, "disk": {"used": ..., "total": ...},
   "temp": 73.0,
   "terminals": {"t9": {"cpu": 12.0, "rss": 4.9e8, "procs": 4}, ...}}

A CPU é a diferença entre esta leitura e a anterior (guardada em
$XDG_RUNTIME_DIR/wrath-espirito.json). O consumo por terminal soma os processos
que herdaram HC_TERMINAL_ID do Herdr, isto é, tudo o que cada sandestin abriu.
Só lê /proc e /sys; não precisa de nada instalado. Linux apenas.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.expanduser("~/.claude/grimorio"))
try:
    import guardiao  # encantamentos de cada sandestin + último ato do guardião
except Exception:
    guardiao = None

STATE = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "wrath-espirito.json")
TICK = os.sysconf("SC_CLK_TCK")
PAGE = os.sysconf("SC_PAGE_SIZE")


def cpu_totals():
    parts = open("/proc/stat").readline().split()[1:]
    vals = [int(x) for x in parts]
    idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
    return sum(vals), idle


def meminfo():
    m = {}
    for line in open("/proc/meminfo"):
        k, v = line.split(":", 1)
        m[k] = int(v.split()[0]) * 1024
    return m


def temperature():
    zones = "/sys/class/thermal"
    found = {}
    for z in os.listdir(zones):
        if not z.startswith("thermal_zone"):
            continue
        try:
            kind = open(f"{zones}/{z}/type").read().strip()
            found[kind] = int(open(f"{zones}/{z}/temp").read()) / 1000
        except Exception:
            pass
    for kind in ("x86_pkg_temp", "TCPU", "cpu_thermal", "acpitz"):
        if kind in found and found[kind] > 0:
            return round(found[kind], 1)
    plausible = [v for v in found.values() if 15 < v < 120]
    return round(max(plausible), 1) if plausible else None


def terminals():
    out = {}
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            with open(f"/proc/{pid}/environ", "rb") as f:
                env = f.read().split(b"\0")
            tid = next((e[15:].decode() for e in env if e.startswith(b"HC_TERMINAL_ID=")), None)
            if not tid:
                continue
            stat = open(f"/proc/{pid}/stat").read()
            fields = stat[stat.rindex(")") + 2:].split()
            jiffies = int(fields[11]) + int(fields[12])  # utime + stime
            rss = int(open(f"/proc/{pid}/statm").read().split()[1]) * PAGE
        except Exception:
            continue
        t = out.setdefault(tid, {"jiffies": 0, "rss": 0, "procs": 0, "pids": {}})
        t["pids"][pid] = jiffies
        t["rss"] += rss
        t["procs"] += 1
    return out


def main():
    now = time.time()
    total, idle = cpu_totals()
    terms = terminals()
    try:
        prev = json.load(open(STATE))
    except Exception:
        prev = {}
    cpu = None
    if prev.get("total") and total > prev["total"]:
        dt = total - prev["total"]
        cpu = round(100 * (1 - (idle - prev["idle"]) / dt), 1)
    cores = os.cpu_count() or 1
    elapsed = now - prev.get("at", now)
    result_terms = {}
    for tid, t in terms.items():
        used = 0
        old = prev.get("pids", {}).get(tid, {})
        for pid, j in t["pids"].items():
            if pid in old:
                used += max(0, j - old[pid])
        share = round(100 * used / TICK / elapsed / cores, 1) if elapsed > 0.2 and old else None
        result_terms[tid] = {"cpu": share, "rss": t["rss"], "procs": t["procs"]}
    spells, guard, gj = {}, None, {}
    if guardiao:
        try:
            procs = guardiao.read_procs()
            gj = guardiao.jiffies_snapshot(procs)
            for s in guardiao.sandestins(procs, prev.get("gj"), elapsed if elapsed > 0.2 else None):
                if s["terminal"] and s["spells"]:
                    spells[s["terminal"]] = s["spells"]
            cfg = guardiao.load_config()
            try:
                last = json.load(open(guardiao.EVENT))
            except Exception:
                last = None
            guard = {"ativo": cfg["ativo"], "simular": cfg["simular"], "ultimo": last}
        except Exception:
            pass
    for tid, sp in spells.items():
        result_terms.setdefault(tid, {"cpu": None, "rss": 0, "procs": 0})["spells"] = sp
    json.dump({"at": now, "total": total, "idle": idle, "gj": gj,
               "pids": {tid: t["pids"] for tid, t in terms.items()}}, open(STATE, "w"))

    m = meminfo()
    st = os.statvfs("/")
    print(json.dumps({
        "cpu": cpu,
        "cores": cores,
        "load": [float(x) for x in open("/proc/loadavg").read().split()[:3]],
        "mem": {"used": m["MemTotal"] - m.get("MemAvailable", m["MemFree"]), "total": m["MemTotal"]},
        "swap": {"used": m.get("SwapTotal", 0) - m.get("SwapFree", 0), "total": m.get("SwapTotal", 0)},
        "disk": {"used": (st.f_blocks - st.f_bfree) * st.f_frsize, "total": st.f_blocks * st.f_frsize},
        "temp": temperature(),
        "terminals": result_terms,
        "guarda": guard,
        "at": now,
    }))


if __name__ == "__main__":
    main()
