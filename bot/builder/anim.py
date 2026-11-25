"""Slaýd geçişleri (transition) we elementleriň animasiýasy (PowerPoint XML)."""
from __future__ import annotations

from lxml import etree
from pptx.oxml.ns import qn

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"
P14_NS = "http://schemas.microsoft.com/office/powerpoint/2010/main"
P159_NS = "http://schemas.microsoft.com/office/powerpoint/2015/09/main"

TRANSITIONS = {
    "fade": "<p:fade/>",
    "push": '<p:push dir="u"/>',
    "wipe": '<p:wipe dir="r"/>',
    "cover": '<p:cover dir="l"/>',
    "split": '<p:split orient="vert" dir="out"/>',
}


def _remove_transition(sld):
    for tag in (qn("p:transition"), f"{{{MC_NS}}}AlternateContent"):
        for el in sld.findall(tag):
            sld.remove(el)


def _insert(sld, el):
    """Tertip: cSld, clrMapOvr, transition, timing."""
    anchor = sld.find(qn("p:clrMapOvr"))
    if anchor is None:
        anchor = sld.find(qn("p:cSld"))
    if el.tag == qn("p:timing"):
        tr = sld.find(qn("p:transition"))
        if tr is None:
            tr = sld.find(f"{{{MC_NS}}}AlternateContent")
        if tr is not None:
            anchor = tr
    anchor.addnext(el)


def add_transition(slide, kind: str = "fade", speed: str = "med"):
    sld = slide._element
    _remove_transition(sld)
    if kind == "morph":
        # Morph (Transformasiýa) PowerPoint 2019+/365-de; köne programmalarda fade görkezilýär
        xml = (
            f'<mc:AlternateContent xmlns:mc="{MC_NS}">'
            f'<mc:Choice xmlns:p159="{P159_NS}" Requires="p159">'
            f'<p:transition xmlns:p="{P_NS}" xmlns:p14="{P14_NS}" spd="slow" p14:dur="1600">'
            f'<p159:morph option="byObject"/></p:transition></mc:Choice>'
            f'<mc:Fallback><p:transition xmlns:p="{P_NS}" spd="slow"><p:fade/></p:transition></mc:Fallback>'
            f'</mc:AlternateContent>'
        )
    else:
        xml = (f'<p:transition xmlns:p="{P_NS}" spd="{speed}">'
               f'{TRANSITIONS.get(kind, TRANSITIONS["fade"])}</p:transition>')
    _insert(sld, etree.fromstring(xml))


# Effekt görnüşleri: (presetID, presetSubtype, filter or None)
EFFECTS = {
    "fade": (10, 0, "fade"),
    "rise": (42, 0, "fade"),          # aşakdan ýuwaşlyk bilen ýokary galýar
    "wipe_up": (22, 4, "wipe(up)"),   # aşakdan ýokary açylýar (diagramma sütünleri)
    "wipe_left": (22, 8, "wipe(left)"),
    "zoom": (53, 16, "fade"),         # kiçiden ulalýar
}


def _tgt(spid):
    return f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl>'


def _anim_prop(nid, spid, attr, frm, to, dur):
    return (
        f'<p:anim calcmode="lin" valueType="num"><p:cBhvr><p:cTn id="{nid()}" dur="{dur}" decel="100000" fill="hold"/>'
        f'{_tgt(spid)}<p:attrNameLst><p:attrName>{attr}</p:attrName></p:attrNameLst></p:cBhvr>'
        f'<p:tavLst><p:tav tm="0"><p:val><p:strVal val="{frm}"/></p:val></p:tav>'
        f'<p:tav tm="100000"><p:val><p:strVal val="{to}"/></p:val></p:tav></p:tavLst></p:anim>'
    )


def add_animations(slide, steps, step_ms=300, dur_ms=600):
    """steps: [(shape, effect), ...]. Slaýd açylanda awtomatik yzly-yzyna oýnaýar.
    effect: fade | rise | wipe_up | wipe_left | zoom | kenburns (surat ýuwaş ulalýar)"""
    steps = [(s, e) for s, e in steps if s is not None]
    if not steps:
        return
    sld = slide._element
    old = sld.find(qn("p:timing"))
    if old is not None:
        sld.remove(old)

    cid = [3]

    def nid():
        cid[0] += 1
        return cid[0]

    pars = []
    t = 0
    for i, (shp, eff) in enumerate(steps):
        spid = shp.shape_id
        node = "afterEffect" if i == 0 else "withEffect"
        if eff == "kenburns":
            # Emfaza: surat 8 sekundyň dowamynda 6% ulalýar
            pars.append(
                f'<p:par><p:cTn id="{nid()}" presetID="6" presetClass="emph" presetSubtype="0" fill="hold" nodeType="{node}">'
                f'<p:stCondLst><p:cond delay="{t}"/></p:stCondLst><p:childTnLst>'
                f'<p:animScale><p:cBhvr><p:cTn id="{nid()}" dur="8000" decel="100000" fill="hold"/>{_tgt(spid)}</p:cBhvr>'
                f'<p:by x="106000" y="106000"/></p:animScale></p:childTnLst></p:cTn></p:par>'
            )
            continue
        preset, sub, flt = EFFECTS.get(eff, EFFECTS["fade"])
        extra = ""
        if eff == "zoom":
            extra = (_anim_prop(nid, spid, "ppt_w", "0", "#ppt_w", dur_ms)
                     + _anim_prop(nid, spid, "ppt_h", "0", "#ppt_h", dur_ms))
        elif eff == "rise":
            extra = (_anim_prop(nid, spid, "ppt_x", "#ppt_x", "#ppt_x", dur_ms)
                     + _anim_prop(nid, spid, "ppt_y", "#ppt_y+0.08", "#ppt_y", dur_ms))
        d = dur_ms * 2 if eff == "wipe_up" else dur_ms
        pars.append(
            f'<p:par><p:cTn id="{nid()}" presetID="{preset}" presetClass="entr" presetSubtype="{sub}" fill="hold" nodeType="{node}">'
            f'<p:stCondLst><p:cond delay="{t}"/></p:stCondLst><p:childTnLst>'
            f'<p:set><p:cBhvr><p:cTn id="{nid()}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>'
            f'{_tgt(spid)}<p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr>'
            f'<p:to><p:strVal val="visible"/></p:to></p:set>'
            f'<p:animEffect transition="in" filter="{flt}"><p:cBhvr><p:cTn id="{nid()}" dur="{d}"/>'
            f'{_tgt(spid)}</p:cBhvr></p:animEffect>{extra}</p:childTnLst></p:cTn></p:par>'
        )
        t += step_ms

    xml = (
        f'<p:timing xmlns:p="{P_NS}"><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>'
        f'<p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>'
        f'<p:par><p:cTn id="3" fill="hold"><p:stCondLst><p:cond delay="indefinite"/>'
        f'<p:cond evt="onBegin" delay="0"><p:tn val="2"/></p:cond></p:stCondLst><p:childTnLst>'
        f'<p:par><p:cTn id="{nid()}" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
        + "".join(pars)
        + '</p:childTnLst></p:cTn></p:par>'
        '</p:childTnLst></p:cTn></p:par>'
        '</p:childTnLst></p:cTn><p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>'
        '<p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst></p:seq>'
        '</p:childTnLst></p:cTn></p:par></p:tnLst></p:timing>'
    )
    _insert(sld, etree.fromstring(xml))


def add_entrance(slide, shapes, effect="fade", step_ms=350, dur_ms=600):
    """Köne interfeýs: ähli shape-lere bir effekt."""
    effs = [effect] if isinstance(effect, str) else list(effect)
    add_animations(slide, [(s, effs[i % len(effs)]) for i, s in enumerate(shapes)], step_ms, dur_ms)
