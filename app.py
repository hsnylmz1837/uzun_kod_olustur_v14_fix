
import io, re, os, math, unicodedata
from pathlib import Path
import pandas as pd
import numpy as np
import streamlit as st
import qrcode

st.set_page_config(page_title="Uzun Kod — v14 / Statik", page_icon="🧩", layout="wide", initial_sidebar_state="collapsed")

# Light look tweaks: white cards, hidden sidebar.
st.markdown("""
<style>
[data-testid="stSidebar"]{display:none!important;}
[data-testid="collapsedControl"]{display:none!important;}
.block-container{padding-top:1.2rem;padding-bottom:2rem;}
.white-panel{background:#ffffff;color:#111827;padding:20px;border-radius:12px;box-shadow:0 2px 14px rgba(0,0,0,0.05);margin-bottom:14px;border:1px solid #e5e7eb;}
.code-panel{background:#ffffff;color:#111827;padding:20px;border-radius:12px;box-shadow:0 2px 14px rgba(0,0,0,0.05);border:1px solid #e5e7eb;}
button[role="tab"]>div>p{font-weight:600;}
[data-baseweb="notification"][kind="info"] {background:#fae8d7!important;color:#4b5563!important;}
</style>
""", unsafe_allow_html=True)

# Header
left, right = st.columns([6,1])
with left:
    st.title("Uzun Kod Oluşturma Programı - v14 / Statik")
    st.caption("Format: 'MakineTipi' + seçilen 'ValueCode'lar + sayısal alanlar (önek/sonek/ondalık).")
with right:
    for p in ["data/coiltech_logo.png","coiltech_logo.png","static/coiltech_logo.png"]:
        try:
            st.image(p, use_container_width=True); break
        except: pass

@st.cache_data
def read_schema(file)->dict:
    xls = pd.ExcelFile(file)
    dfs = {
        "products": pd.read_excel(xls, "products"),
        "sections": pd.read_excel(xls, "sections"),
        "fields":   pd.read_excel(xls, "fields"),
        "options":  pd.read_excel(xls, "options"),
    }
    for col in ["PrereqFieldKey","PrereqAllowValues","SuffixKey","EncodeKey","Decimals","Widget"]:
        if col not in dfs["fields"].columns:
            dfs["fields"][col] = np.nan if col=="Decimals" else ""
    return dfs

schema = read_schema("data/schema.xlsx")

def clean_str(x:str)->str:
    try:
        if x is None: return ""
        if isinstance(x, float) and math.isnan(x): return ""
        s = str(x)
        if s.lower() == "nan": return ""
        return s
    except Exception:
        return ""

def sanitize_codes_only(s:str)->str:
    return re.sub(r"[^A-Z0-9._-]", "", str(s).upper()) if s is not None else ""

def norm(s): 
    return str(s).strip().casefold()

def is_skip_valuecode(code):
    return norm(code) in {"yok","diger","diğer","var"}

def normalize_prereq(x):
    if x is None: return ""
    s = str(x).strip()
    if s == "" or s.lower() in {"nan","none"}: return ""
    try:
        if isinstance(x, float) and math.isnan(x): return ""
    except Exception:
        pass
    return s

def parse_allow_values(s):
    s = (s or "").strip()
    if not s: return set()
    return {v.strip() for v in s.split(",") if v.strip()}

def prereq_met(field_key, allow_values)->bool:
    fk = normalize_prereq(field_key)
    if not fk: return True
    v = st.session_state["form_values"].get(fk)
    if v in (None, "", []): return False
    allow = parse_allow_values(allow_values)
    if not allow: return True
    if isinstance(v, list):
        return any(sanitize_codes_only(x) in {sanitize_codes_only(a) for a in allow} for x in v)
    return sanitize_codes_only(v) in {sanitize_codes_only(a) for a in allow}

def format_number_for_code(n, pad, decimals):
    if decimals is None or (isinstance(decimals,float) and math.isnan(decimals)):
        decimals = 0
    try:
        nf = float(n)
    except Exception:
        return str(n)
    if int(decimals) == 0:
        nv = int(round(nf))
        if pad is None or (isinstance(pad, float) and math.isnan(pad)) or (isinstance(pad, str) and pad.strip()==""):
            return str(nv)
        if isinstance(pad, (int, float)) and not (isinstance(pad, float) and math.isnan(pad)):
            return f"{nv:0{int(pad)}d}"
        if isinstance(pad, str) and pad.isdigit():
            return f"{nv:0{int(pad)}d}"
        if isinstance(pad, str) and "." in pad:
            w = pad.split(".")[0]
            return f"{nv:0{int(w)}d}"
        return str(nv)
    else:
        d = int(decimals)
        s = f"{nf:.{d}f}"
        return s

# Emoji mapping with TR normalize
def tr_norm(s):
    if s is None: return ""
    s = str(s)
    tr_map = str.maketrans({'İ':'I','I':'I','ı':'I','Ş':'S','ş':'S','Ğ':'G','ğ':'G','Ü':'U','ü':'U','Ö':'O','ö':'O','Ç':'C','ç':'C'})
    s = s.translate(tr_map)
    s = unicodedata.normalize('NFKD', s).encode('ascii','ignore').decode('ascii')
    s = re.sub(r"[^A-Z0-9]+"," ", s.upper()).strip()
    return s

EMOJI_ASCII = {
    "ELK":"⚡","ELEKTRIK":"⚡",
    "ACICI TIPI":"🧰","ACICI":"🧰",
    "CIFT KAFA":"🔁",
    "SAC GENISLIGI":"📐",
    "DIS CAP":"📏",
    "ACICI BASKI TIPI":"🖨️",
    "TAHRIK":"⚙️",
    "TAMBUR TIPI":"🎛️","TAMBUR":"🎛️",
    "TAMBUR HIZ":"⏱️",
    "MERKEZLEME":"🎯",
    "YUKLEME ARABASI":"🛻",
    "HIDROLIK UNITE":"🛢️",
    "LOOP KONTROL SISTEMI TIPI":"🔄","LOOP KONTROL":"🔄",
    "YON":"🧭"
}
def emoji_for(section_key, section_label):
    keys = [section_key or "", section_label or ""]
    for k in keys:
        k1 = tr_norm(k)
        if k1 in EMOJI_ASCII:
            return EMOJI_ASCII[k1]
    k2 = (section_key or "").upper()
    return {"ELK":"⚡","ACICI_TIPI":"🧰","CIFT_KAFA":"🔁","SAC_GEN":"📐","DISCAP":"📏","YON":"🧭"}.get(k2,"•")

# ---- STATE ----
if "step" not in st.session_state: st.session_state["step"] = 1
if "s1" not in st.session_state: st.session_state["s1"] = None
if "s2" not in st.session_state: st.session_state["s2"] = None
if "product_row" not in st.session_state: st.session_state["product_row"] = None
if "form_values" not in st.session_state: st.session_state["form_values"] = {}

S1_ORDER = ["Rulo Besleme","Plaka Besleme","Tamamlayıcı Ürünler"]

def big_buttons(options, cols=3, key_prefix="bb"):
    cols_list = st.columns(cols); clicked=None
    for i, opt in enumerate(options):
        with cols_list[i % cols]:
            if st.button(opt, key=f"{key_prefix}_{opt}", use_container_width=True):
                clicked = opt
    return clicked

# ---- Step 1 ----
if st.session_state["step"] == 1:
    st.markdown('<div class="white-panel">', unsafe_allow_html=True)
    st.header("Aşama 1 — Ürün ve Detay ↪️")
    s1_candidates = [x for x in S1_ORDER if x in schema["products"]["Kategori1"].unique().tolist()]
    clicked = big_buttons(s1_candidates, cols=3, key_prefix="s1")
    st.markdown('</div>', unsafe_allow_html=True)
    if clicked:
        st.session_state["s1"] = clicked
        st.session_state["s2"] = None
        st.session_state["product_row"] = None
        st.session_state["form_values"] = {}
        st.session_state["step"] = 2
        st.rerun()

# ---- Step 2 ----
elif st.session_state["step"] == 2:
    st.markdown('<div class="white-panel">', unsafe_allow_html=True)
    st.header("Aşama 2 — Alt Seçim")
    st.write(f"Seçimler: **{st.session_state['s1']}**")
    sub = schema["products"].query("Kategori1 == @st.session_state['s1']")["Kategori2"].dropna().unique().tolist()
    clicked = big_buttons(sub, cols=3, key_prefix="s2")
    col_back, _ = st.columns([1,1])
    with col_back:
        if st.button("⬅️ Geri (Aşama 1)"):
            st.session_state["step"] = 1; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    if clicked:
        st.session_state["s2"] = clicked
        st.session_state["product_row"] = None
        st.session_state["form_values"] = {}
        st.session_state["step"] = 3
        st.rerun()

# ---- Step 3 ----
else:
    s1, s2 = st.session_state["s1"], st.session_state["s2"]
    st.markdown('<div class="white-panel">', unsafe_allow_html=True)
    st.header("Aşama 3 — Ürün ve Detay 🔗")
    st.write(f"Seçimler: **{s1} → {s2}**")
    prods = schema["products"].query("Kategori1 == @s1 and Kategori2 == @s2")
    if prods.empty:
        st.warning("Bu seçim için 'products' sayfasında satır yok.")
    else:
        display = prods["UrunAdi"] + " — " + prods["MakineTipi"]
        choice = st.selectbox("Ürün", options=display.tolist(), placeholder="Seçiniz")
        if choice:
            idx = display.tolist().index(choice)
            row = prods.iloc[idx]
            st.session_state["product_row"] = row

    row = st.session_state["product_row"]
    if row is not None:
        mk = row["MakineTipi"]
        st.info(f"Seçilen makine: **{mk}** — Kod: **{row['UrunKodu']}**")
        secs = schema["sections"].query("Kategori1 == @s1 and Kategori2 == @s2 and MakineTipi == @mk").sort_values("Order")
        if secs.empty:
            st.warning("Bu makine için 'sections' sayfasında kayıt yok.")
        else:
            tab_labels = [f"{emoji_for(sec.SectionKey, sec.SectionLabel)} {sec.SectionLabel}" for _, sec in secs.iterrows()]
            tabs = st.tabs(tab_labels)
            fdf = schema["fields"]; optdf = schema["options"]
            for i, (_, sec) in enumerate(secs.iterrows()):
                with tabs[i]:
                    fields = fdf.query("SectionKey == @sec.SectionKey")
                    if fields.empty:
                        st.write("Alan yok."); continue
                    for _, fld in fields.iterrows():
                        k = fld["FieldKey"]; label = fld["FieldLabel"]; typ = str(fld["Type"]).lower(); req = bool(fld["Required"]); default = fld.get("Default")
                        prereq_key = fld.get("PrereqFieldKey"); allow_vals = fld.get("PrereqAllowValues")
                        fk = normalize_prereq(prereq_key)
                        enabled = prereq_met(prereq_key, allow_vals)

                        if not enabled and fk:
                            pr_label_row = fdf.query("FieldKey == @fk")
                            if not pr_label_row.empty:
                                target_label = pr_label_row.iloc[0]["FieldLabel"]
                                allow = parse_allow_values(allow_vals)
                                hint = f"🔒 Bu alan, önce **{target_label}** için seçim yapıldığında aktif olur."
                                if allow:
                                    hint = f"🔒 Bu alan, **{target_label}** alanında **{', '.join(sorted(allow))}** seçildiğinde aktif olur."
                                st.caption(hint)

                        widget = str(fld.get("Widget") or "").strip().lower()
                        if typ in ("select", "multiselect"):
                            opts = optdf.query("OptionsKey == @fld.OptionsKey").sort_values("Order")
                            opts_codes = opts["ValueCode"].astype(str).tolist()
                            opts_labels = (opts["ValueCode"].astype(str) + " — " + opts["ValueLabel"].astype(str)).tolist()

                            if typ == "select":
                                if widget == "radio":
                                    sel = st.radio(label + (" *" if req else ""), options=opts_codes, format_func=lambda c: opts_labels[opts_codes.index(c)], index=None, key=f"k_{k}", disabled=not enabled, horizontal=False)
                                else:  # combo
                                    sel = st.selectbox(label + (" *" if req else ""), options=opts_codes, format_func=lambda c: opts_labels[opts_codes.index(c)], index=None, key=f"k_{k}", disabled=not enabled, placeholder="Seçiniz")
                                if enabled and sel is not None:
                                    st.session_state["form_values"][k] = sel
                                else:
                                    st.session_state["form_values"].pop(k, None)

                            else:  # multiselect
                                if widget == "checkboxes":
                                    selected = []
                                    for code, lbl in zip(opts_codes, opts_labels):
                                        checked = st.checkbox(lbl, key=f"chk_{k}_{code}", value=False, disabled=not enabled)
                                        if checked: selected.append(code)
                                    if enabled and selected: st.session_state["form_values"][k] = selected
                                    else: st.session_state["form_values"].pop(k, None)
                                else:
                                    ms = st.multiselect(label + (" *" if req else ""), options=opts_codes, default=[], format_func=lambda c: opts_labels[opts_codes.index(c)], key=f"k_{k}", disabled=not enabled, placeholder="Seçiniz")
                                    if enabled and ms: st.session_state["form_values"][k] = ms
                                    else: st.session_state["form_values"].pop(k, None)

                        elif typ == "number":
                            minv = fld.get("Min"); maxv = fld.get("Max"); step = fld.get("Step")
                            decimals = fld.get("Decimals"); d = int(decimals) if pd.notna(decimals) else 0
                            if pd.isna(step): step = 1 if d == 0 else 10**(-d)
                            if d == 0:
                                minv_i = int(minv) if pd.notna(minv) else None
                                maxv_i = int(maxv) if pd.notna(maxv) else None
                                defv_i = int(default) if pd.notna(default) else (minv_i or 0)
                                step_i = int(step)
                                val = st.number_input(label + (" *" if req else ""), min_value=minv_i, max_value=maxv_i, value=defv_i, step=step_i, format="%d", key=f"k_{k}", disabled=not enabled)
                            else:
                                fmt = f"%.{d}f"
                                minv_f = float(minv) if pd.notna(minv) else None
                                maxv_f = float(maxv) if pd.notna(maxv) else None
                                defv_f = float(default) if pd.notna(default) else (minv_f or 0.0)
                                step_f = float(step)
                                val = st.number_input(label + (" *" if req else ""), min_value=minv_f, max_value=maxv_f, value=defv_f, step=step_f, format=fmt, key=f"k_{k}", disabled=not enabled)
                            if enabled: st.session_state["form_values"][k] = val
                        else:
                            txt = st.text_input(label + (" *" if req else ""), value=clean_str(default), key=f"k_{k}", disabled=not enabled, placeholder="Seçiniz")
                            if enabled and txt.strip() != "": st.session_state["form_values"][k] = txt
                            else: st.session_state["form_values"].pop(k, None)
    st.markdown('</div>', unsafe_allow_html=True)

    # Bottom panel with code + QR
    st.markdown('<div class="code-panel">', unsafe_allow_html=True)
    def build_linear_code(machine_type, values, schema, s1, s2):
        parts = []; m = sanitize_codes_only(machine_type) if machine_type else ""
        if m: parts.append(m)
        secs = schema["sections"].query("Kategori1 == @s1 and Kategori2 == @s2 and MakineTipi == @machine_type").sort_values("Order")
        fdf = schema["fields"]; optdf = schema["options"]
        for _, sec in secs.iterrows():
            fields = fdf.query("SectionKey == @sec.SectionKey")
            for _, fld in fields.iterrows():
                k = fld["FieldKey"]; typ = str(fld["Type"]).lower(); val = st.session_state['form_values'].get(k)
                if val in (None, "", [], 0): continue
                if typ == "select":
                    if is_skip_valuecode(val): continue
                    parts.append(sanitize_codes_only(val))
                elif typ == "multiselect" and isinstance(val, list):
                    subset = optdf.query("OptionsKey == @fld.OptionsKey")
                    order_map = {str(r["ValueCode"]): int(r["Order"]) for _, r in subset.iterrows()}
                    clean = [v for v in val if not is_skip_valuecode(v)]
                    ordered = sorted(clean, key=lambda v: order_map.get(str(v), 999999))
                    if ordered: parts.append("".join([sanitize_codes_only(v) for v in ordered]))
                elif typ == "number":
                    decimals = fld.get("Decimals")
                    num = format_number_for_code(val, fld.get("Pad"), decimals)
                    pre = clean_str(fld.get("EncodeKey")); suf = clean_str(fld.get("SuffixKey"))
                    piece = f"{pre}{num}{suf}" if (pre or suf) else f"{num}"
                    parts.append(piece)
                else:
                    txt = clean_str(val); pre = clean_str(fld.get("EncodeKey")); suf = clean_str(fld.get("SuffixKey"))
                    piece = f"{pre}{txt}{suf}" if (pre or suf) else txt
                    if piece.strip(): parts.append(piece)
        return " ".join([p for p in parts if p])

    c1, c2 = st.columns([3,1])
    with c1:
        if st.button("🔐 Uzun Kodu Oluştur (Linear)") and st.session_state.get("product_row") is not None:
            row = st.session_state["product_row"]
            code = build_linear_code(row["MakineTipi"], st.session_state.get("form_values", {}), schema, s1, s2)
            st.session_state["long_code"] = code
        if "long_code" in st.session_state and st.session_state["long_code"]:
            st.success("Uzun kod üretildi")
            st.code(st.session_state["long_code"], language="text")
    with c2:
        if "long_code" in st.session_state and st.session_state["long_code"]:
            code = st.session_state["long_code"]
            img = qrcode.make(code); buf = io.BytesIO(); img.save(buf, format="PNG"); st.image(buf.getvalue(), caption="QR")
            st.download_button("Kodu TXT indir", data=code.encode("utf-8"), file_name="uzun_kod.txt")
    st.markdown('</div>', unsafe_allow_html=True)
