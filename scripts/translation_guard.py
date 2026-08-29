#!/usr/bin/env python3
"""Protect Markdown structures before translation and verify exact restoration.

This module does not translate text. It tokenizes code fences, inline code, math,
HTML blocks, link destinations and URLs so a translator can process only prose.
"""
from __future__ import annotations
import hashlib, json, re
from dataclasses import dataclass
PROTECTED=[
 re.compile(r'```.*?```',re.S), re.compile(r'~~~.*?~~~',re.S),
 re.compile(r'(?<!`)`[^`\n]+`(?!`)'),
 re.compile(r'\$\$.*?\$\$',re.S), re.compile(r'(?<!\$)\$(?!\$).*?(?<!\$)\$(?!\$)',re.S),
 re.compile(r'(?m)^\s*<[^>]+>.*$'),
 re.compile(r'(?<=\]\()[^)]+(?=\))'),
 re.compile(r'https?://[^\s)>]+'),
]
@dataclass
class Bundle:
 text:str
 values:list[str]
 hashes:list[str]
def protect(text:str)->Bundle:
    spans=[]
    for pattern in PROTECTED:
        spans.extend((m.start(),m.end()) for m in pattern.finditer(text))
    merged=[]
    for start,end in sorted(spans):
        if merged and start<merged[-1][1]:
            if end>merged[-1][1]: merged[-1]=(merged[-1][0],end)
        else: merged.append((start,end))
    out=[];values=[];hashes=[];cursor=0
    for i,(start,end) in enumerate(merged):
        out.append(text[cursor:start]); value=text[start:end]; token=f'⟦CPUZ_PROTECTED_{i:05d}⟧'
        out.append(token); values.append(value); hashes.append(hashlib.sha256(value.encode()).hexdigest()); cursor=end
    out.append(text[cursor:])
    return Bundle(''.join(out),values,hashes)
def restore(translated:str,bundle:Bundle)->str:
    out=translated
    for i,value in enumerate(bundle.values):
        token=f'⟦CPUZ_PROTECTED_{i:05d}⟧'
        if out.count(token)!=1: raise ValueError(f'protected token {token} occurs {out.count(token)} times')
        out=out.replace(token,value)
    return out
def verify(restored:str,bundle:Bundle)->None:
    check=protect(restored)
    if check.hashes!=bundle.hashes: raise ValueError('protected structures changed or reordered')
