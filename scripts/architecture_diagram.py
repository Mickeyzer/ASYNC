"""Render a vector diagram of the implemented web onboarding flow."""
import html
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'submission'
WIDTH,HEIGHT=1920,1280


def render_architecture():
    ink='#20252e';muted='#586675';red='#ad1930';blue='#28618b';purple='#685095';green='#23634d'
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="diagram-title diagram-description">',
        '<title id="diagram-title">Udyam Digital: implemented web architecture</title>',
        '<desc id="diagram-description">Customer web interface and optional browser speech connect to a FastAPI backend. Backend rules own catalogue recommendations, pricing, document validation and simulated orders. Gemini supplies consented structured drafts and extracted fields. Source CSVs, SQLite records and temporary memory have distinct roles.</desc>',
        '<defs>']
    for name,color in [('main',red),('speech',blue),('provider',purple),('data',green)]:
        parts.append(f'<marker id="{name}-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="{color}"/></marker>')
    parts.append('</defs><rect width="1920" height="1280" fill="#fff"/>')

    def text(x,y,value,size=20,color=ink,weight=400):
        parts.append(f'<text x="{x}" y="{y}" font-family="Arial,sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}">{html.escape(value)}</text>')

    def panel(x,y,w,h,label,subtitle,color,fill):
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{fill}" stroke="{color}" stroke-width="1.5"/>')
        text(x+24,y+38,label,24,color,700);text(x+24,y+69,subtitle,19,muted)

    def edge(path,name='main',both=False,dashed=False):
        color={'main':red,'speech':blue,'provider':purple,'data':green}[name]
        parts.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2.5" marker-end="url(#{name}-arrow)"'+(f' marker-start="url(#{name}-arrow)"' if both else '')+(' stroke-dasharray="7 5"' if dashed else '')+'/>')

    def card(x,y,w,h,title,lines,color=ink,fill='#fff',border='#d7dee7',dashed=False,size=20):
        parts.append(f'<g data-card="{x},{y},{w},{h}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" stroke="{border}" stroke-width="1.5"'+(' stroke-dasharray="7 5"' if dashed else '')+'/>')
        text(x+20,y+36,title,24,color,700)
        for i,line in enumerate(lines):text(x+20,y+73+i*28,line,size,muted)
        parts.append('</g>')

    parts.append(f'<rect x="48" y="40" width="6" height="65" rx="3" fill="{red}"/>')
    text(72,75,'Udyam Digital',40,ink,700)
    text(72,108,'Digital onboarding for Accel Business | implemented web prototype',22,muted)
    text(1260,72,'GEMINI: DRAFTS + EXTRACTION',21,purple,700)
    text(1260,104,'BACKEND: RULES + DECISIONS',21,red,700)
    parts.append('<rect x="48" y="140" width="1824" height="48" rx="8" fill="#f5f7fa"/>')
    text(72,171,'01 Review business needs',21,ink,600);text(452,171,'02 Edit catalogue estimate',21,ink,600)
    text(900,171,'03 Consent + document checks',21,ink,600);text(1400,171,'04 Simulated order + tracker',21,ink,600)
    for x in [400,846,1345]:text(x,171,'>',24,red,700)

    panel(48,214,450,670,'CUSTOMER / BROWSER','React + TypeScript | responsive web app',blue,'#f6f8fb')
    panel(560,214,790,670,'FASTAPI BACKEND','Authoritative rules, access checks and workflow',red,'#fcf6f7')
    panel(1410,214,462,670,'GEMINI API (EXTERNAL)','Server-side adapter; HTTPS provider calls',purple,'#f8f6fc')
    panel(48,968,1824,248,'LOCAL DATA + RETENTION','Different stores for source rules, saved records and temporary fields',green,'#f5f9f6')

    # Connections use the whitespace between components rather than crossing text.
    edge('M474 376H584',both=True);text(480,356,'JSON / images',14,red,600)
    edge('M272 518V490','speech')
    edge('M272 664V714','speech',True,True)
    text(290,695,'Audio / transcript',17,blue)
    edge('M1326 538H1378V391H1434','provider',True)
    edge('M1326 756H1388V502H1434','provider',True)
    edge('M967 543H943')
    edge('M967 758H943')
    edge('M584 584H530V926H322V968','data',True)
    text(64,916,'Read-only catalogue / registry lookups',18,green)
    edge('M950 884V928H887V968','data',True)
    text(970,951,'Save / reopen records',18,green)
    edge('M1146 864V916H1530V968','data')
    text(1560,947,'Temporary fields',18,green)

    card(72,312,402,178,'Customer workspace',[
        'Create account / sign in; English / Hindi',
        'Reviewed needs; editable bundle / quote',
        'Document upload, checkout and tracker',
        'Reviewed chat stays in the open tab',
    ],size=19)
    card(72,518,402,146,'Optional voice input',[
        'Separate speech consent + permission',
        'Editable transcript; owner confirms',
        'Transcript becomes advisor description',
    ],blue,size=19)
    card(72,714,402,146,'Browser speech service',[
        'en-IN / hi-IN recognition',
        'May use an external speech provider',
        'Audio is not stored by this application',
    ],blue,border=blue,dashed=True,size=19)

    card(584,312,742,120,'API boundary + account access',[
        'Validated schemas, request/rate limits and HttpOnly session cookie',
        'Argon2id password hashes; account ownership and staff roles',
    ],red)
    card(584,460,359,174,'Catalogue + quote rules',[
        'Select catalogue starter services',
        'Eligibility and product dependencies',
        'Quantities, fees and contract terms',
    ],red,size=18)
    card(967,460,359,174,'Advisor adapter',[
        'Consented text + reviewed facts',
        'Bounded follow-up conversation',
        'Validated draft; guided fallback',
    ],purple,size=18)
    card(584,674,359,190,'Order state machine',[
        'Passing checks + accepted terms',
        'Recheck quote; prevent duplicates',
        'Accepted > installation > activation',
        'All service stages are simulated',
    ],red,size=18)
    card(967,674,359,190,'Document pipeline',[
        'PNG/JPEG, max 5 MB; strip metadata',
        'Extract fields; owner reviews',
        'Mock registries, dates, consistency',
        'Unresolved issues block checkout',
    ],red,size=18)

    card(1434,312,414,244,'Structured assistance',[
        'Business text > structured needs draft',
        'Document pixels > extracted fields',
        'Backend validates returned JSON',
        'Provider never sets catalogue prices',
        'Provider never approves checkout',
    ],purple,size=19)
    card(1434,600,414,260,'Provider controls',[
        'API key stays on the server',
        'Only consented text / pixels are sent',
        '60-second request; one attempt',
        'Advisor outage: guided questions',
        'OCR outage: retry; no guessed fields',
        'Provider data terms apply separately',
    ],purple,size=19)

    card(72,1054,500,138,'Read-only source CSVs',[
        '25 products + mock GSTIN / Udyam registries',
        'Deterministic catalogue and registry checks',
    ],green,size=19)
    card(596,1054,594,146,'SQLite: two local databases',[
        'accounts.sqlite3: password hashes + hashed sessions',
        'onboarding.sqlite3: consent, summaries, quotes, orders',
        'Journeys 24 h; sessions 8 h; inactive accounts 30 d',
    ],green,size=18)
    card(1214,1054,634,146,'Temporary server memory',[
        'Extracted fields: up to 30 min; cleared on order submission',
        'Document images are not persisted by the application',
        'Raw fields are lost on server restart',
    ],green,size=18)
    text(48,1245,'Demo scope: no real payment, availability check, installation or activation. Local SQLite is not encrypted.',18,muted)
    text(48,1272,'Additional web features: consented partner follow-up and authorized review. These are outside the main recorded flow.',17,muted)
    parts.append('</svg>')
    return ''.join(parts)


def write_architecture(destination=OUT):
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    svg=render_architecture()
    (destination/'architecture.svg').write_text(svg,encoding='utf-8')
    from playwright.sync_api import sync_playwright
    from pypdf import PdfReader
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        try:
            page=browser.new_page(viewport={'width':WIDTH,'height':HEIGHT},device_scale_factor=1)
            page.set_content(f'<html><head><title>Udyam Digital web architecture</title><style>@page{{size:{WIDTH}px {HEIGHT}px;margin:0}}html,body{{margin:0;width:{WIDTH}px;height:{HEIGHT}px;overflow:hidden}}svg{{display:block;width:{WIDTH}px;height:{HEIGHT}px}}</style></head><body>'+svg+'</body></html>')
            overflow=page.locator('[data-card]').evaluate_all('''nodes=>nodes.flatMap(n=>{const [x,y,w,h]=n.dataset.card.split(',').map(Number);return [...n.querySelectorAll('text')].filter(t=>{const b=t.getBBox();return b.x<x+12||b.y<y+10||b.x+b.width>x+w-12||b.y+b.height>y+h-8;}).map(t=>t.textContent);})''')
            if overflow:raise ValueError('Diagram text exceeds its card: '+repr(overflow))
            page.pdf(path=str(destination/'Architecture.pdf'),prefer_css_page_size=True,print_background=True)
            page.screenshot(path=str(destination/'architecture-preview.png'),full_page=True)
        finally:
            browser.close()
    if len(PdfReader(destination/'Architecture.pdf').pages)!=1:raise ValueError('Architecture must fit one page.')
    print(json.dumps({'architecture':'implemented web flow','pages':1,'width':WIDTH,'height':HEIGHT,'text_overflow':False,'provider_calls':0}))


if __name__=='__main__':write_architecture()
