"""Slaýd geçişleri (transition) we elementleriň animasiýasy (PowerPoint XML)."""
from __future__ import annotations

from lxml import etree
from pptx.oxml.ns import qn

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"

TRANSITIONS = {
    "fade": '<p:fade xmlns:p="%s"/>' % P_NS,
    "push": '<p:push xmlns:p="%s" dir="u"/>' % P_NS,
    "wipe": '<p:wipe xmlns:p="%s" dir="r"/>' % P_NS,
    "cover": '<p:cover xmlns:p="%s" dir="l"/>' % P_NS,
    "split": '<p:split xmlns:p="%s" orient="vert" dir="out"/>' % P_NS,
}


def _insert_after_clrmap(sld, el):
    """p:transition / p:timing elementleri p:clrMapOvr-dan soň durmaly."""
    anchor = sld.find(qn("p:clrMapOvr"))
    if anchor is None:
        anchor = sld.find(qn("p:cSld"))
    # transition timing-den öň bolmaly
    if el.tag == qn("p:timing"):
        tr = sld.find(qn("p:transition"))
        if tr is not None:
            anchor = tr
    anchor.addnext(el)


def add_transition(slide, kind: str = "fade", speed: str = "med"):
    sld = slide._element
    old = sld.find(qn("p:transition"))
    if old is not None:
        sld.remove(old)
    tr = etree.SubElement(sld, qn("p:transition"))
    sld.remove(tr)
    tr.set("spd", speed)
    tr.append(etree.fromstring(TRANSITIONS.get(kind, TRANSITIONS["fade"])))
    _insert_after_clrmap(sld, tr)


# Effekt görnüşleri: (presetID, presetSubtype, filter)
EFFECTS = {
    "fade": (10, 0, "fade"),
    "wipe_up": (22, 1, "wipe(down)"),
    "wipe_left": (22, 8, "wipe(left)"),
    "zoom": (53, 16, "fade"),
}


def add_entrance(slide, shapes, effect="fade", step_ms=350, dur_ms=600):
    """Slaýd açylanda shape-ler yzly-yzyna awtomatik peýda bolýar."""
    shapes = [s for s in shapes if s is not None]
    if not shapes:
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
    for i, shp in enumerate(shapes):
        eff = effect if isinstance(effect, str) else effect[i % len(effect)]
        preset, sub, flt = EFFECTS.get(eff, EFFECTS["fade"])
        spid = shp.shape_id
        a, b, c = nid(), nid(), nid()
        node = "afterEffect" if i == 0 else "withEffect"
        extra = ""
        if eff == "zoom":
            extra = (
                f'<p:anim calcmode="lin" valueType="num"><p:cBhvr><p:cTn id="{nid()}" dur="{dur_ms}" fill="hold"/>'
                f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl><p:attrNameLst><p:attrName>ppt_w</p:attrName></p:attrNameLst></p:cBhvr>'
                f'<p:tavLst><p:tav tm="0"><p:val><p:fltVal val="0"/></p:val></p:tav><p:tav tm="100000"><p:val><p:strVal val="#ppt_w"/></p:val></p:tav></p:tavLst></p:anim>'
                f'<p:anim calcmode="lin" valueType="num"><p:cBhvr><p:cTn id="{nid()}" dur="{dur_ms}" fill="hold"/>'
                f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl><p:attrNameLst><p:attrName>ppt_h</p:attrName></p:attrNameLst></p:cBhvr>'
                f'<p:tavLst><p:tav tm="0"><p:val><p:fltVal val="0"/></p:val></p:tav><p:tav tm="100000"><p:val><p:strVal val="#ppt_h"/></p:val></p:tav></p:tavLst></p:anim>'
            )
        pars.append(
            f'<p:par><p:cTn id="{a}" presetID="{preset}" presetClass="entr" presetSubtype="{sub}" fill="hold" nodeType="{node}">'
            f'<p:stCondLst><p:cond delay="{i * step_ms}"/></p:stCondLst><p:childTnLst>'
            f'<p:set><p:cBhvr><p:cTn id="{b}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>'
            f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl><p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr>'
            f'<p:to><p:strVal val="visible"/></p:to></p:set>'
            f'<p:animEffect transition="in" filter="{flt}"><p:cBhvr><p:cTn id="{c}" dur="{dur_ms}"/>'
            f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl></p:cBhvr></p:animEffect>'
            f'{extra}</p:childTnLst></p:cTn></p:par>'
        )

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
    _insert_after_clrmap(sld, etree.fromstring(xml))
