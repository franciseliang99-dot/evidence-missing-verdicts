"""Model backends. Endpoints come from a config file outside the repo
(default ~/.config/apart-epistemics/backends.json) so no host addresses or keys live in git.

Config shape:
  {"<name>": {"kind": "ollama", "url": "http://127.0.0.1:11434"},
   "<name>": {"kind": "openai", "url": "http://host:port/v1", "keychain_service": "SERVICE"}}
API keys are read from the macOS login keychain at call time and never logged.
"""
import json
import os
import subprocess
import time
import urllib.request

CFG = os.environ.get("EPI_BACKENDS", os.path.expanduser("~/.config/apart-epistemics/backends.json"))


def _cfg():
    with open(CFG) as f:
        return json.load(f)


def _key(service):
    r = subprocess.run(["/usr/bin/security", "find-generic-password", "-s", service, "-w"],
                       capture_output=True, text=True, timeout=10)
    if r.returncode != 0:
        raise RuntimeError(f"keychain lookup failed for service {service!r} (rc {r.returncode})")
    return r.stdout.strip()


def _post(url, body, headers, timeout):
    req = urllib.request.Request(url, json.dumps(body).encode(),
                                 {"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def generate(model_spec, system, prompt, max_tokens=200, timeout=600):
    """model_spec = "<backend>:<model name>". Returns (text, info dict). Temperature 0."""
    backend, model = model_spec.split(":", 1)
    b = _cfg()[backend]
    t0 = time.time()
    if b["kind"] == "ollama":
        r = _post(b["url"] + "/api/chat", {
            "model": model, "stream": False, "think": False,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            "options": {"temperature": 0, "num_predict": max_tokens, "seed": 0}}, {}, timeout)
        text = r["message"]["content"]
        info = {"in_tok": r.get("prompt_eval_count"), "out_tok": r.get("eval_count")}
    elif b["kind"] == "openai":
        r = _post(b["url"] + "/chat/completions", {
            "model": model, "temperature": 0, "max_tokens": max_tokens, "stream": False, "seed": 0,
            "chat_template_kwargs": {"enable_thinking": False},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]},
            {"Authorization": "Bearer " + _key(b["keychain_service"])}, timeout)
        text = r["choices"][0]["message"].get("content") or ""
        u = r.get("usage") or {}
        info = {"in_tok": u.get("prompt_tokens"), "out_tok": u.get("completion_tokens")}
    else:
        raise ValueError(b["kind"])
    info["sec"] = round(time.time() - t0, 2)
    return text, info


def list_models(backend):
    b = _cfg()[backend]
    if b["kind"] == "ollama":
        with urllib.request.urlopen(b["url"] + "/api/tags", timeout=20) as r:
            return [m["name"] for m in json.load(r)["models"]]
    req = urllib.request.Request(b["url"] + "/models",
                                 headers={"Authorization": "Bearer " + _key(b["keychain_service"])})
    with urllib.request.urlopen(req, timeout=20) as r:
        return [m["id"] for m in json.load(r)["data"]]
