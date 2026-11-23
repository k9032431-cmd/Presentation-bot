"""Başlangyç stiller. Admin bot arkaly täze stil goşup bilýär.

Her stil:
  name       - ady
  bg         - fon reňki
  surface    - kartoçka/blok fony
  primary    - esasy reňk
  secondary  - ikinji reňk
  accent     - üns reňki
  text       - tekst reňki
  muted      - ikinji derejeli tekst
  font       - sözbaşy şrifti
  body_font  - tekst şrifti
  motif      - bezeg görnüşi: wave | circles | blocks | diagonal | minimal | frame
"""

DEFAULT_STYLES = [
    {
        "name": "Corporate Blue",
        "bg": "#FFFFFF", "surface": "#EEF4FB", "primary": "#0B3C78", "secondary": "#1F7AE0",
        "accent": "#38BDF8", "text": "#13233A", "muted": "#5B6B80",
        "font": "Segoe UI", "body_font": "Calibri", "motif": "wave",
    },
    {
        "name": "Emerald Business",
        "bg": "#FFFFFF", "surface": "#EAF4F0", "primary": "#0E4D3C", "secondary": "#16805F",
        "accent": "#34D399", "text": "#10231D", "muted": "#5D7069",
        "font": "Segoe UI", "body_font": "Calibri", "motif": "blocks",
    },
    {
        "name": "Dark Luxury",
        "bg": "#14110F", "surface": "#221E1A", "primary": "#C8A97E", "secondary": "#8C7355",
        "accent": "#E9D8BE", "text": "#F3EDE4", "muted": "#A89C8C",
        "font": "Georgia", "body_font": "Calibri", "motif": "frame",
    },
    {
        "name": "Ocean Teal",
        "bg": "#FFFFFF", "surface": "#E7F5F6", "primary": "#0F5C6B", "secondary": "#1597A8",
        "accent": "#5ED1D9", "text": "#0F2A30", "muted": "#557278",
        "font": "Segoe UI", "body_font": "Calibri", "motif": "circles",
    },
    {
        "name": "Sunset Pitch",
        "bg": "#FFF8F2", "surface": "#FFE9DA", "primary": "#E8572A", "secondary": "#B5179E",
        "accent": "#FFB347", "text": "#2A1A1F", "muted": "#7A5F63",
        "font": "Segoe UI", "body_font": "Calibri", "motif": "diagonal",
    },
    {
        "name": "Minimal Gray",
        "bg": "#FAFAFA", "surface": "#EFEFEF", "primary": "#222222", "secondary": "#555555",
        "accent": "#E63946", "text": "#1A1A1A", "muted": "#6E6E6E",
        "font": "Arial", "body_font": "Arial", "motif": "minimal",
    },
    {
        "name": "Royal Purple",
        "bg": "#0F0C29", "surface": "#1D1846", "primary": "#8B5CF6", "secondary": "#6366F1",
        "accent": "#F0ABFC", "text": "#F5F3FF", "muted": "#A5A1C9",
        "font": "Segoe UI", "body_font": "Calibri", "motif": "circles",
    },
    {
        "name": "Navy Gold",
        "bg": "#0B1F3A", "surface": "#142B4D", "primary": "#F2B705", "secondary": "#D99404",
        "accent": "#FFE08A", "text": "#F4F6FA", "muted": "#9FB0C8",
        "font": "Georgia", "body_font": "Calibri", "motif": "diagonal",
    },
]

MOTIFS = ["wave", "circles", "blocks", "diagonal", "minimal", "frame"]
FONTS = ["Arial", "Calibri", "Georgia", "Segoe UI", "Verdana", "Times New Roman"]
