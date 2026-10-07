#!/usr/bin/env python3
"""Run a rendered what-if page's script headless (no browser) and print what it would show.

Needs py_mini_racer: python3 -m venv V && V/bin/pip install mini-racer; then V/bin/python jstest_headless.py PAGE.html
For every chunk size and view it prints the total tiles; then it presses the first target button and
prints the gap table. Compare against the adapter's reconstruction before publishing.
"""
import json
import re
import sys

from py_mini_racer import MiniRacer

STUB = r"""
var created = [], charts = [];
function El(tag){ this.tag=tag; this.children=[]; this.listeners={}; this.style={setProperty:function(){}}; this.attrs={}; this._h=""; this.textContent=""; this.value=""; created.push(this);}
Object.defineProperty(El.prototype,"innerHTML",{get:function(){return this._h;},set:function(v){this._h=v; if(v==="") this.children=[];}});
El.prototype.appendChild=function(c){this.children.push(c); return c;};
El.prototype.append=function(){for (var i=0;i<arguments.length;i++) this.children.push(arguments[i]);};
El.prototype.addEventListener=function(t,f){(this.listeners[t]=this.listeners[t]||[]).push(f);};
El.prototype.setAttribute=function(k,v){this.attrs[k]=v;};
var byId={};
var document={ getElementById:function(id){ return byId[id]||(byId[id]=new El(id)); }, createElement:function(t){return new El(t);}, documentElement:{} };
function getComputedStyle(){ return {getPropertyValue:function(){return "#336699";}}; }
var window={ matchMedia:function(){return {addEventListener:function(){}};} };
function MutationObserver(){ this.observe=function(){}; }
function Chart(el,cfg){ this.cfg=cfg; charts.push(this); this.destroy=function(){}; }
"""


def main():
    html = open(sys.argv[1]).read()
    script = re.findall(r"<script>(.*?)</script>", html, re.S)[-1].replace("const PROFILE = /*", "var PROFILE = /*")
    ctx = MiniRacer()
    ctx.eval(STUB + script)
    prof = json.loads(ctx.eval("JSON.stringify(PROFILE)"))

    def click(text):
        ctx.eval("(function(){var e=created.filter(function(x){return x.textContent==%s && x.listeners.click;});"
                 "e[e.length-1].listeners.click[0]();})()" % json.dumps(text))

    def tiles():
        return json.loads(ctx.eval("JSON.stringify(byId['tiles'].children.map(function(d){"
                                   "return d.innerHTML.replace(/<[^>]+>/g,' ').replace(/\\s+/g,' ').trim();}))"))

    views = [p["label"] for p in prof["presets"]] + ["What-if"]
    for C in sorted(prof["chunks"], key=int):
        click(C)
        ctx.eval("byId['resetBtn'].listeners.click[0]()")
        for v in views:
            click(v)
            print(f"[chunk {C}] {v}")
            for t in tiles():
                print("   ", t)
        if prof.get("target_presets"):
            tp = prof["target_presets"][0]["label"]
            click("What-if")
            click("Set " + re.sub(r"^Target:\s*", "target: ", tp, flags=re.I))
            print(f"[chunk {C}] What-if after '{tp}':")
            for t in tiles():
                print("   ", t)
            ctx.eval("byId['resetBtn'].listeners.click[0]()")
            click(prof["presets"][-1]["label"])
            print("   ", ctx.eval("byId['gapNote'].textContent"))
            table = ctx.eval("byId['gapTable'].innerHTML")
            for row in re.findall(r"<tr>(.*?)</tr>", table, re.S):
                print("    " + " | ".join(x.strip() for x in re.sub(r"<[^>]+>", "|", row).split("|") if x.strip()))
    print("charts built:", ctx.eval("charts.length"))


if __name__ == "__main__":
    main()
