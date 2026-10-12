"""الهوية البصرية: «سوق الليل» — خلفية بترولية عميقة، زعفران للسعر، ورد للأرخص، نعناع للقيمة، وأشكال بطاقات الأسعار.

الحركة مقصودة وقليلة: تأرجح بطاقة السعر في الواجهة (لحظة واحدة مميزة)، رسم الحلقات والأشرطة عند ظهور النتائج،
وتفاعلات hover/active على العناصر التي يضغط عليها المستخدم. وتُعطَّل كلها مع prefers-reduced-motion.
"""
import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;500;600&family=Reem+Kufi:wght@500;700&display=swap');

:root{
  --ink:#0C2327; --ink-deep:#071417; --panel:#123036; --panel-2:#17404A;
  --saffron:#F5B335; --hibiscus:#EF476F; --mint:#35D39A; --lagoon:#3AA7C9;
  --sand:#F1E8D4; --muted:#9DB4B5; --line:rgba(241,232,212,.14);
  --display:'Reem Kufi','Segoe UI',Tahoma,sans-serif;
  --body:'IBM Plex Sans Arabic','Segoe UI',Tahoma,sans-serif;
  --ease:cubic-bezier(.2,.8,.2,1);
}

/* ---------- الأساس ---------- */
html, body, .stApp, [data-testid="stMarkdownContainer"], label, input, textarea, button p, .stTabs [data-baseweb="tab"]{
  font-family:var(--body);
}
.stApp{
  direction:rtl; color:var(--sand);
  background:
    radial-gradient(1100px 520px at 90% -12%, rgba(58,167,201,.20), transparent 60%),
    radial-gradient(900px 480px at 0% 8%, rgba(245,179,53,.10), transparent 60%),
    var(--ink);
}
.stApp::before{            /* ثقوب لوحة الأسعار (pegboard) */
  content:""; position:fixed; inset:0; z-index:0; pointer-events:none;
  background-image:radial-gradient(rgba(241,232,212,.09) 1px, transparent 1.3px);
  background-size:24px 24px;
  -webkit-mask-image:linear-gradient(to bottom,#000,transparent 65%); mask-image:linear-gradient(to bottom,#000,transparent 65%);
}
[data-testid="stHeader"]{background:transparent}
footer, #MainMenu{visibility:hidden}
.block-container{padding-top:2rem; max-width:1180px; position:relative; z-index:1}
:focus-visible{outline:2px solid var(--saffron)!important; outline-offset:2px}
::selection{background:var(--saffron); color:#2a1d00}

/* ---------- الشريط الجانبي ---------- */
[data-testid="stSidebar"]{background:linear-gradient(180deg,var(--ink-deep),var(--ink)); border-right:1px solid var(--line)}
[data-testid="stSidebar"] *{direction:rtl}
.side-brand{display:flex; align-items:center; gap:.7rem; margin:.2rem 0 1rem}
.side-brand .mark{width:38px; height:38px; background:var(--saffron); color:#2a1d00; display:grid; place-items:center;
  font-family:var(--display); font-weight:700; font-size:1.2rem;
  clip-path:polygon(18% 0,82% 0,100% 20%,100% 100%,0 100%,0 20%)}
.side-brand b{font-family:var(--display); font-size:1.25rem}
.side-brand small{display:block; color:var(--muted); font-size:.75rem}

/* ---------- مدخلات ---------- */
input, textarea{unicode-bidi:plaintext; text-align:start}
[data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="select"]>div, [data-baseweb="textarea"]{
  background:var(--panel)!important; border-radius:12px!important; border-color:var(--line)!important;
  transition:border-color .2s, box-shadow .2s;
}
[data-baseweb="input"]:focus-within, [data-baseweb="select"]>div:focus-within{
  border-color:var(--saffron)!important; box-shadow:0 0 0 3px rgba(245,179,53,.18);
}
[data-testid="stForm"]{border:1px solid var(--line); border-radius:18px; background:rgba(255,255,255,.02)}

/* ---------- أزرار ---------- */
.stButton>button, .stDownloadButton>button, [data-testid="stFormSubmitButton"]>button, [data-testid="stLinkButton"] a{
  position:relative; overflow:hidden; border-radius:12px; border:1px solid var(--line);
  background:var(--panel-2); color:var(--sand); font-weight:600;
  transition:transform .18s var(--ease), box-shadow .25s, border-color .2s, background .2s;
}
.stButton>button:hover, .stDownloadButton>button:hover, [data-testid="stFormSubmitButton"]>button:hover, [data-testid="stLinkButton"] a:hover{
  transform:translateY(-2px); border-color:var(--saffron); color:var(--sand); box-shadow:0 8px 22px rgba(0,0,0,.35);
}
.stButton>button:active, [data-testid="stFormSubmitButton"]>button:active, [data-testid="stLinkButton"] a:active{transform:translateY(0) scale(.98)}
button[data-testid^="stBaseButton-primary"]{
  background:linear-gradient(135deg,var(--saffron),#FF8F3D)!important; color:#2a1d00!important; border:none!important;
}
button[data-testid^="stBaseButton-primary"]:hover{box-shadow:0 10px 28px rgba(245,179,53,.38)!important}
button[data-testid^="stBaseButton-primary"]::after{        /* لمعة تمرّ عند الإشارة بالماوس */
  content:""; position:absolute; top:0; bottom:0; width:40%; left:-60%;
  background:linear-gradient(100deg,transparent,rgba(255,255,255,.45),transparent); transform:skewX(-20deg);
}
button[data-testid^="stBaseButton-primary"]:hover::after{left:130%; transition:left .7s var(--ease)}

/* ---------- تبويبات ---------- */
[data-baseweb="tab-list"]{gap:.3rem; border-bottom:1px solid var(--line)}
[data-baseweb="tab"]{border-radius:12px 12px 0 0; padding:.6rem 1.1rem; color:var(--muted); transition:color .2s, background .2s}
[data-baseweb="tab"]:hover{background:rgba(255,255,255,.04); color:var(--sand)}
[data-baseweb="tab"][aria-selected="true"]{color:var(--saffron)}
[data-baseweb="tab-highlight"]{background:var(--saffron)!important; height:3px!important}
[data-baseweb="tab-border"]{background:transparent!important}
[data-testid="stDataFrame"]{border:1px solid var(--line); border-radius:14px; overflow:hidden}
[data-testid="stAlert"]{border-radius:14px}

/* ---------- الواجهة (Hero) ---------- */
.hero{position:relative; display:grid; grid-template-columns:1fr 230px; gap:2rem; align-items:center;
  padding:2.4rem 2.6rem; border-radius:28px; overflow:hidden;
  background:linear-gradient(135deg,rgba(23,64,74,.95),rgba(12,35,39,.95)); border:1px solid var(--line)}
.hero.compact{grid-template-columns:1fr; padding:1.2rem 1.6rem; border-radius:20px}
.hero h1{font-family:var(--display); font-weight:700; font-size:clamp(1.9rem,4vw,3.1rem); line-height:1.3; margin:0 0 .7rem; color:var(--sand)}
.hero.compact h1{font-size:1.5rem; margin:0}
.hero p{max-width:58ch; color:var(--muted); line-height:1.95; margin:0 0 1.2rem}
.chips{display:flex; flex-wrap:wrap; gap:.5rem}
.chip{padding:.35rem .85rem; border:1px solid var(--line); border-radius:99px; font-size:.85rem; background:rgba(255,255,255,.04)}

.tag-wrap{position:relative; height:250px; display:flex; justify-content:center}
.swing{transform-origin:50% 0; animation:swing 5.5s ease-in-out infinite; display:flex; flex-direction:column; align-items:center}
.string{width:2px; height:70px; background:linear-gradient(var(--line),var(--sand))}
.tag{position:relative; width:158px; padding:2.3rem 1rem 1.4rem; text-align:center; color:#2a1d00;
  background:linear-gradient(160deg,#FFD067,var(--saffron)); font-family:var(--display);
  clip-path:polygon(16% 0,84% 0,100% 13%,100% 100%,0 100%,0 13%)}
.tag::before{content:""; position:absolute; top:.65rem; left:50%; width:16px; height:16px; margin-left:-8px; border-radius:50%; background:var(--ink)}
.tag b{display:block; font-size:1.55rem; line-height:1.25}
.tag span{font-size:.95rem; opacity:.8}
@keyframes swing{0%,100%{transform:rotate(-7deg)} 50%{transform:rotate(7deg)}}

/* ---------- شريط المتاجر ---------- */
.ticker{direction:ltr; overflow:hidden; margin:1.1rem 0 .4rem; padding:.55rem 0; border-block:1px dashed var(--line);
  -webkit-mask-image:linear-gradient(90deg,transparent,#000 12%,#000 88%,transparent); mask-image:linear-gradient(90deg,transparent,#000 12%,#000 88%,transparent)}
.ticker-track{display:inline-flex; gap:2.6rem; white-space:nowrap; animation:marquee 32s linear infinite; color:var(--muted); font-size:.9rem}
.ticker:hover .ticker-track{animation-play-state:paused}
@keyframes marquee{to{transform:translateX(-50%)}}

/* ---------- عناوين الأقسام ---------- */
.sec{display:flex; align-items:center; gap:.7rem; margin:1.9rem 0 .9rem; font-family:var(--display); font-size:1.4rem}
.sec::before{content:""; width:16px; height:16px; background:var(--saffron); clip-path:polygon(0 0,70% 0,100% 50%,70% 100%,0 100%)}
.sec small{font-family:var(--body); font-size:.85rem; color:var(--muted); margin-inline-start:.4rem}

/* ---------- بطاقات المؤشرات ---------- */
.stats{display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:1rem}
.stat{position:relative; padding:1.05rem 1.3rem 1.05rem 1.1rem; border-radius:18px; background:var(--panel); border:1px solid var(--line); overflow:hidden;
  animation:rise .7s var(--ease) both; animation-delay:calc(var(--i,0) * 90ms)}
.stat::after{content:""; position:absolute; inset-block:0; inset-inline-start:0; width:5px; background:var(--accent,var(--saffron))}
.stat .lbl{font-size:.85rem; color:var(--muted)}
.stat .val{font-family:var(--display); font-size:2rem; font-weight:700; font-variant-numeric:tabular-nums; margin:.1rem 0}
.stat .val small{font-size:.9rem; color:var(--muted); font-weight:500; margin-inline-start:.3rem}
.stat .sub{font-size:.82rem; color:var(--muted); overflow:hidden; text-overflow:ellipsis; white-space:nowrap}
@keyframes rise{from{opacity:0; transform:translateY(14px)}}

/* ---------- حلقات القياس ---------- */
.gauges{display:flex; flex-wrap:wrap; gap:1.6rem; align-items:center; padding:1.2rem 1.5rem; border-radius:20px; background:var(--panel); border:1px solid var(--line)}
.gauge{display:flex; align-items:center; gap:1rem}
.ring{position:relative; width:112px; height:112px; flex:none}
.ring svg{transform:rotate(-90deg); width:100%; height:100%}
.ring .track{stroke:rgba(241,232,212,.12)}
.ring .bar{stroke:var(--c,var(--mint)); stroke-linecap:round; stroke-dasharray:264; stroke-dashoffset:264;
  animation:draw 1.3s .25s var(--ease) forwards}
.ring .num{position:absolute; inset:0; display:grid; place-items:center; font-family:var(--display); font-size:1.5rem}
.gauge .txt b{display:block; font-family:var(--display); font-size:1.1rem}
.gauge .txt span{color:var(--muted); font-size:.85rem}
@keyframes draw{to{stroke-dashoffset:calc(264 * (1 - var(--p,0)))}}
.insight{flex:1; min-width:220px; color:var(--sand); line-height:2}
.insight div::before{content:"✦ "; color:var(--saffron)}

/* ---------- تذكرة العرض ---------- */
.ticket-wrap{filter:drop-shadow(0 12px 16px rgba(0,0,0,.30)); transition:transform .28s var(--ease); margin-bottom:.6rem}
.ticket-wrap:hover{transform:translateY(-5px)}
.ticket{--r:11px; height:262px; display:grid; grid-template-rows:66% 34%; border-radius:18px;
  background:linear-gradient(170deg,var(--panel-2),var(--panel));
  -webkit-mask:radial-gradient(var(--r) at 0 66%,#0000 97%,#000) left/51% 100% no-repeat, radial-gradient(var(--r) at 100% 66%,#0000 97%,#000) right/51% 100% no-repeat;
          mask:radial-gradient(var(--r) at 0 66%,#0000 97%,#000) left/51% 100% no-repeat, radial-gradient(var(--r) at 100% 66%,#0000 97%,#000) right/51% 100% no-repeat}
.ticket .top{padding:1.1rem 1.3rem .6rem; overflow:hidden}
.ticket .store{font-family:var(--display); font-size:1.05rem; margin:.55rem 0 .25rem; direction:ltr; text-align:right}
.ticket .ttl{color:var(--muted); font-size:.85rem; line-height:1.7; display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden}
.ticket .bottom{border-top:2px dashed var(--line); padding:.6rem 1.3rem .7rem; display:flex; flex-direction:column; justify-content:center; gap:.35rem}
.ticket .price{font-family:var(--display); font-size:1.55rem; font-weight:700; color:var(--saffron); font-variant-numeric:tabular-nums}
.ticket .price small{font-size:.8rem; color:var(--muted); margin-inline-start:.3rem}
.badge{display:inline-block; padding:.2rem .7rem; border-radius:99px; font-size:.78rem; font-weight:600; color:#06201a; background:var(--mint)}
.badge.cheap{background:var(--hibiscus); color:#2b0510}
.badge.safe{background:var(--lagoon); color:#04202a}
.badge.pulse{animation:pulse 2.2s ease-out infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(53,211,154,.55)} 70%,100%{box-shadow:0 0 0 11px rgba(53,211,154,0)}}
.meter{height:7px; border-radius:99px; background:rgba(241,232,212,.1); overflow:hidden}
.meter i{display:block; height:100%; width:calc(var(--w,0) * 1%); border-radius:inherit; transform-origin:right;
  background:linear-gradient(90deg,var(--lagoon),var(--mint)); animation:grow 1s .3s var(--ease) both}
@keyframes grow{from{transform:scaleX(0)}}
.rate{font-size:.8rem; color:var(--muted); display:flex; justify-content:space-between}
.stars{color:var(--saffron); letter-spacing:.1em}

/* ---------- مراجعات وبدائل ---------- */
.quote{margin:.5rem 0; padding:.75rem 1.1rem; line-height:1.9; border-radius:12px; background:rgba(255,255,255,.03);
  border-inline-start:4px solid var(--lagoon); transition:background .2s, transform .2s var(--ease)}
.quote:hover{background:rgba(255,255,255,.07); transform:translateX(-3px)}
.quote.pos{border-color:var(--mint)} .quote.neg{border-color:var(--hibiscus)}
.alt{padding:1rem 1.2rem; margin-bottom:.4rem; border-radius:16px; background:var(--panel); border:1px solid var(--line)}
.alt b{font-family:var(--display)} .alt p{color:var(--muted); margin:.4rem 0 0; line-height:1.8; font-size:.9rem}

/* ---------- حالة البداية والتحميل ---------- */
.steps{display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:1rem; margin-top:1.2rem}
.step{padding:1.1rem 1.3rem; border-radius:18px; border:1px dashed var(--line); background:rgba(255,255,255,.02)}
.step b{font-family:var(--display); font-size:1.05rem; display:block; margin-bottom:.3rem}
.step span{color:var(--muted); font-size:.9rem; line-height:1.8}
.step .n{display:inline-grid; place-items:center; width:28px; height:28px; margin-inline-end:.5rem; border-radius:50%; background:var(--saffron); color:#2a1d00; font-family:var(--display)}
.skel-grid{display:grid; grid-template-columns:repeat(3,1fr); gap:1rem; margin-top:1rem}
.skel{height:150px; border-radius:18px; background:linear-gradient(100deg,var(--panel) 30%,var(--panel-2) 50%,var(--panel) 70%); background-size:220% 100%; animation:shimmer 1.3s linear infinite}
.skel.s{height:84px}
@keyframes shimmer{to{background-position:-220% 0}}
.foot{margin-top:2.2rem; padding-top:1rem; border-top:1px dashed var(--line); color:var(--muted); font-size:.82rem; line-height:1.9}
.err{padding:.9rem 1.2rem; border-radius:14px; background:rgba(239,71,111,.12); border:1px solid rgba(239,71,111,.4); margin:.8rem 0}

@media (max-width:820px){
  .hero{grid-template-columns:1fr; padding:1.5rem}
  .tag-wrap{display:none}
  .skel-grid{grid-template-columns:1fr}
}
@media (prefers-reduced-motion:reduce){
  *, *::before, *::after{animation:none!important; transition:none!important}
  .ring .bar{stroke-dashoffset:calc(264 * (1 - var(--p,0)))}
}
</style>
"""


class ThemeManager:
    @staticmethod
    def inject() -> None:
        st.html(CSS)
