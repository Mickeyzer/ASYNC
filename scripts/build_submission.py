"""Build a reviewable deck and PDFs from supplied branding and reproducible evidence."""
import base64
import copy
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.lead_analysis import report
from backend.models import QuoteRequest
from backend.quotes import quote

OUT=ROOT/'submission'
TEMPLATE=ROOT/'6ad9d4887d445_airtel_sync/Submission Template_Sync.pptx'
NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main',
    'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
    'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'rel':'http://schemas.openxmlformats.org/package/2006/relationships',
    'ct':'http://schemas.openxmlformats.org/package/2006/content-types'}
for prefix in ('p','a','r'):ET.register_namespace(prefix,NS[prefix])


def content():
    evidence=report()
    profile={'business_type':'clinic','city_tier':1,'employees':5,'sites':1,'monthly_budget':3000,
             'current_internet':'hotspot','gstin_claim':'yes','needs':['internet','email'],'language':'en'}
    estimate=quote(QuoteRequest(profile=profile,items=[{'product_id':'P01','quantity':1},{'product_id':'P16','quantity':5}]),'unverified')
    professional=next(s for s in evidence['segments'] if s['segment']=='Professional offices')
    return [
      {'title':'Udyam Digital','lines':['From business needs to a tracked demo order',
        'Self-serve acquisition with people for the exceptions','Enterprise Track A | Synthetic-data prototype'],
       'source':'Working local prototype. Payments, availability and activation are simulated.'},
      {'title':'Start where quote drop-off hurts','lines':[
        f"Only {evidence['activated']} of {evidence['leads']:,} supplied leads activated ({evidence['activation_rate']:.2%}).",
        'Needs assessed: 1,974; quotes accepted: 861. Only 43.6% make that transition.',
        f"Priority segment: professional offices, {professional['leads']:,} leads and {professional['activation_rate']:.2%} historical activation.",
        'Clinics, CA firms and coaching centres: dependable internet, email and basic security.',
        'Value: an understandable bundle, visible fees, fewer document hand-offs and a saved status view.'],
       'source':'Source: supplied synthetic leads and brief. Segment priority is a proposed pilot choice, not proven optimal.'},
      {'title':'Compete on the complete journey','lines':[
        'JioBusiness Solution: integrated connectivity, voice and digital services; bundles already exist.',
        'Vi ReadyForNext: digital-readiness assessment, tailored report and service offers; advice already exists.',
        'Case baseline: field-led discovery, 3-5-day quotes and document collection across channels.',
        'Udyam combines reviewed Hindi/English discovery, editable quotes, mock KYC and a saved tracker.',
        'Positioning hypothesis: reduce owner hand-offs, with consented partner help for exceptions.'],
       'source':'Sources: JioBusiness / Vi official pages, checked 6 Nov 2026; docs/SUBMISSION_SOURCES.md. No full competitor-flow audit.'},
      {'title':'From business needs to an editable quote','lines':[
        'Advisor drafts reviewed needs; catalogue rules control eligibility, dependencies and every price.',
        'Tier-1 clinic, five staff: Biz Fibre 100 at INR 999 + five email seats at INR 125 each.',
        f"Monthly: INR {estimate['monthly_total']:,}. Setup: INR {estimate['setup_total']:,}. First month: INR {estimate['first_month_estimate']:,}. Taxes excluded.",
        'Each service has a 12-month minimum contract; owner can edit quantities and add-ons.',
        'Review estimate, consent to four-document checks, then create and track a simulated order.'],
       'source':'Source: catalogue/quote code at build time. Starter bundle, not a budget optimizer or real commercial offer.'},
      {'title':'Rules, privacy and people protect trust','lines':[
        'React -> FastAPI -> catalogue/mock registries + SQLite. Consented Gemini drafts require review.',
        'Separate consents for drafting, speech, documents and partner contact; images never saved.',
        'Raw fields expire after 30 minutes or order submission; masked journey records after 24 hours.',
        'Account ownership and staff roles limit access. Partners see assigned, consented summaries only.',
        'Original inspection can resolve legibility; missing, expired or inconsistent evidence still blocks.'],
       'source':'Separate architecture diagram and one-page privacy note supplied. Mock checks use 15 July 2026; not compliance certification.'},
      {'title':'Rollout gates and risks','lines':[
        'Now: working synthetic prototype; regression checks cover access, consent, navigation and recovery.',
        'Provider risk: verify live extraction/voice; preserve inputs and guided fallback during outages.',
        'Deployment risk: validate Docker/CI, managed identity, encrypted hosting and operating controls.',
        'Delivery risk: real availability, payment and provisioning need integrations; current stages are simulated.',
        'Next: invited professional-office pilot with partner support and a comparable baseline; WhatsApp stays disabled.'],
       'source':'Proposed rollout, not a production-readiness claim. Acquisition heuristic rejected: top-fifth 7.00% vs 7.08% baseline.'},
      {'title':'Five proposed targets, not claimed results','lines':[
        'Lead-to-activation: historical 7.36%; proposed comparable-cohort target 10%.',
        'Mean lead-to-activation: 17.62 days; proposed target at most 12 days.',
        'Blended acquisition cost: INR 15,053; proposed target at most INR 12,000.',
        'Six-month churn: 15.22%; proposed target at most 12%. Status chases: about 3 to at most 1.',
        'At fixed acquisition spend only, 7.36% to 10% conversion implies about INR 11,079 CAC.'],
       'source':'Scenario arithmetic, not measured savings. Segment pilots need their own comparable baseline; churn needs six months.'},
    ]


def textbox(identifier,x,y,w,h,paragraphs,size=1600,color='172A29',bold=False):
    ns=NS
    shape=ET.Element(f"{{{ns['p']}}}sp")
    nv=ET.SubElement(shape,f"{{{ns['p']}}}nvSpPr")
    ET.SubElement(nv,f"{{{ns['p']}}}cNvPr",id=str(identifier),name=f'Text {identifier}')
    ET.SubElement(nv,f"{{{ns['p']}}}cNvSpPr",txBox='1');ET.SubElement(nv,f"{{{ns['p']}}}nvPr")
    sp=ET.SubElement(shape,f"{{{ns['p']}}}spPr")
    xf=ET.SubElement(sp,f"{{{ns['a']}}}xfrm")
    ET.SubElement(xf,f"{{{ns['a']}}}off",x=str(int(x*914400)),y=str(int(y*914400)))
    ET.SubElement(xf,f"{{{ns['a']}}}ext",cx=str(int(w*914400)),cy=str(int(h*914400)))
    ET.SubElement(sp,f"{{{ns['a']}}}prstGeom",prst='rect');ET.SubElement(sp,f"{{{ns['a']}}}noFill")
    body=ET.SubElement(shape,f"{{{ns['p']}}}txBody")
    ET.SubElement(body,f"{{{ns['a']}}}bodyPr",wrap='square',lIns='0',rIns='0',tIns='0',bIns='0')
    ET.SubElement(body,f"{{{ns['a']}}}lstStyle")
    for line in paragraphs:
        p=ET.SubElement(body,f"{{{ns['a']}}}p")
        pp=ET.SubElement(p,f"{{{ns['a']}}}pPr")
        spacing=ET.SubElement(pp,f"{{{ns['a']}}}spcAft");ET.SubElement(spacing,f"{{{ns['a']}}}spcPts",val='750')
        run=ET.SubElement(p,f"{{{ns['a']}}}r")
        rp=ET.SubElement(run,f"{{{ns['a']}}}rPr",lang='en-US',sz=str(size),b='1' if bold else '0')
        fill=ET.SubElement(rp,f"{{{ns['a']}}}solidFill");ET.SubElement(fill,f"{{{ns['a']}}}srgbClr",val=color)
        ET.SubElement(rp,f"{{{ns['a']}}}latin",typeface='Arial')
        ET.SubElement(run,f"{{{ns['a']}}}t").text=line
    return shape


def pptx(slides):
    with ZipFile(TEMPLATE) as source:files={n:source.read(n) for n in source.namelist()}
    presentation=ET.fromstring(files['ppt/presentation.xml'])
    listing=presentation.find('p:sldIdLst',NS);listing.clear()
    rels=ET.fromstring(files['ppt/_rels/presentation.xml.rels'])
    for rel in list(rels):
        if rel.get('Type','').endswith('/slide'):rels.remove(rel)
    types=ET.fromstring(files['[Content_Types].xml'])
    for override in list(types):
        if '/slides/slide' in override.get('PartName','') or '/notesSlides/' in override.get('PartName',''):types.remove(override)
    outputs={k:v for k,v in files.items() if not k.startswith(('ppt/slides/','ppt/notesSlides/'))}
    for index,data in enumerate(slides,1):
        template=1 if index==1 else 2
        slide=ET.fromstring(files[f'ppt/slides/slide{template}.xml']);tree=slide.find('p:cSld/p:spTree',NS)
        if index==1:
            tree.append(textbox(1001,.6,3.22,5.0,.7,[data['title']],3200,'FFFFFF',True))
            tree.append(textbox(1002,.6,4.0,5.0,1.0,data['lines'],1400,'FFFFFF'))
        else:
            tree.append(textbox(1001,.58,1.0,8.85,.75,[data['title']],2500,'BA261B',True))
            tree.append(textbox(1002,.65,1.88,8.68,2.95,['• '+line for line in data['lines']],1500))
            tree.append(textbox(1003,.65,4.9,8.0,.4,[data['source']],800,'596764'))
        slide_rels=ET.fromstring(files[f'ppt/slides/_rels/slide{template}.xml.rels'])
        for rel in list(slide_rels):
            if rel.get('Type','').endswith('/notesSlide'):slide_rels.remove(rel)
        outputs[f'ppt/slides/slide{index}.xml']=ET.tostring(slide,encoding='utf-8',xml_declaration=True)
        outputs[f'ppt/slides/_rels/slide{index}.xml.rels']=ET.tostring(slide_rels,encoding='utf-8',xml_declaration=True)
        ET.SubElement(listing,f"{{{NS['p']}}}sldId",{'id':str(255+index),f"{{{NS['r']}}}id":f'rId{100+index}'})
        ET.SubElement(rels,f"{{{NS['rel']}}}Relationship",Id=f'rId{100+index}',Type=NS['r']+'/slide',Target=f'slides/slide{index}.xml')
        ET.SubElement(types,f"{{{NS['ct']}}}Override",PartName=f'/ppt/slides/slide{index}.xml',ContentType='application/vnd.openxmlformats-officedocument.presentationml.slide+xml')
    outputs['ppt/presentation.xml']=ET.tostring(presentation,encoding='utf-8',xml_declaration=True)
    outputs['ppt/_rels/presentation.xml.rels']=ET.tostring(rels,encoding='utf-8',xml_declaration=True)
    outputs['[Content_Types].xml']=ET.tostring(types,encoding='utf-8',xml_declaration=True)
    if 'docProps/app.xml' in outputs:
        app_properties=ET.fromstring(outputs['docProps/app.xml'])
        for node in app_properties.iter():
            if node.tag.endswith('}Slides'):node.text=str(len(slides))
            if node.tag.endswith('}Notes'):node.text='0'
        outputs['docProps/app.xml']=ET.tostring(app_properties,encoding='utf-8',xml_declaration=True)
    outputs['docProps/core.xml']=b'''<?xml version="1.0" encoding="UTF-8"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Udyam Digital business case</dc:title><dc:description>Synthetic-data prototype and proposed rollout. Reviewable draft.</dc:description></cp:coreProperties>'''
    root_rels=ET.fromstring(outputs['_rels/.rels'])
    if not any(r.get('Type','').endswith('/metadata/core-properties') for r in root_rels):
        ET.SubElement(root_rels,f"{{{NS['rel']}}}Relationship",Id='rIdUdyamCore',Type=NS['rel']+'/metadata/core-properties',Target='docProps/core.xml')
    if not any(r.get('PartName')=='/docProps/core.xml' for r in types):
        ET.SubElement(types,f"{{{NS['ct']}}}Override",PartName='/docProps/core.xml',ContentType='application/vnd.openxmlformats-package.core-properties+xml')
    outputs['_rels/.rels']=ET.tostring(root_rels,encoding='utf-8',xml_declaration=True)
    outputs['[Content_Types].xml']=ET.tostring(types,encoding='utf-8',xml_declaration=True)
    with ZipFile(OUT/'Udyam_Digital_Business_Case_7_Slides.pptx','w',ZIP_DEFLATED) as archive:
        for name,data in outputs.items():archive.writestr(name,data)


def architecture():
    nodes=[(60,150,'Customer web app','Hindi/English; reviewed voice'),(590,150,'FastAPI + account access','Ownership, roles, bounded work'),
           (1110,150,'Gemini API','Consented text/image drafts'),(60,370,'Catalogue + mock registries','Deterministic rules and prices'),
           (590,370,'Document and order workflow','Checks, review, explicit simulation'),(1110,370,'SQLite stores','Accounts, summaries and events'),
           (60,590,'Assigned partner dashboard','Separate follow-up consent'),(590,590,'Authorized review','Actor, reason, evidence revision'),
           (1110,590,'WhatsApp guided channel','Signed ingress; gated reply adapter')]
    parts=['<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="860" viewBox="0 0 1600 860"><defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="#a43425"/></marker></defs><rect width="1600" height="860" fill="#faf9f4"/><text x="60" y="62" font-family="Arial" font-size="34" fill="#173e37">Udyam Digital · architecture and trust boundaries</text><text x="60" y="105" font-family="Arial" font-size="21" fill="#566760">Synthetic local prototype · AI drafts fields; backend owns eligibility, pricing and order state</text>']
    for d in ['M480 205H590','M1010 205H1110','M690 260V370','M270 370V315H740V260','M1010 425H1110',
              'M270 590V535H690V480','M800 590V480','M1320 590V480']:
        parts.append(f'<path d="{d}" fill="none" stroke="#a43425" stroke-width="3" marker-end="url(#arrow)"/>')
    for x,y,title,subtitle in nodes:
        parts.append(f'<rect x="{x}" y="{y}" width="420" height="110" rx="16" fill="white" stroke="#cfdbd3" stroke-width="2"/><text x="{x+22}" y="{y+43}" font-family="Arial" font-size="24" fill="#173e37">{html.escape(title)}</text><text x="{x+22}" y="{y+79}" font-family="Arial" font-size="19" fill="#566760">{html.escape(subtitle)}</text>')
    parts.append('<text x="60" y="775" font-family="Arial" font-size="20" fill="#173e37">Retention: images never saved · raw fields 30 min · records 24 h · accounts / counters 30 d</text><text x="60" y="815" font-family="Arial" font-size="18" fill="#566760">Channel: encrypted answers 30 min idle / queued replies 10 min. No private record access. Payments and activation simulated.</text></svg>')
    return ''.join(parts)


def main():
    OUT.mkdir(exist_ok=True);(OUT/'assets').mkdir(exist_ok=True)
    slides=content();pptx(slides)
    with ZipFile(TEMPLATE) as source:
        cover=source.read('ppt/media/image2.jpg');inside=source.read('ppt/media/image1.jpg')
    for name,data in [('cover.jpg',cover),('inside.jpg',inside)]: (OUT/'assets'/name).write_bytes(data)
    style='''@page{size:13.333333in 7.5in;margin:0}*{box-sizing:border-box}body{margin:0;font-family:Arial,sans-serif;color:#173e37}.slide{width:1280px;height:720px;position:relative;break-after:page;background-size:cover;padding:125px 78px 70px;overflow:hidden}.slide:last-child{break-after:auto}h1{font-size:36px;color:#ba261b;line-height:1.13;margin:0 0 34px}li{font-size:23px;line-height:1.38;margin:0 0 19px}ul{padding-left:24px}footer{position:absolute;bottom:50px;left:83px;width:1050px;font-size:13px;color:#596764}.cover{padding:415px 72px 40px;color:white}.cover h1{font-size:48px;color:white;margin-bottom:12px}.cover p{font-size:22px;max-width:590px;margin:8px 0}.cover footer{display:none}'''
    sections=[]
    for i,slide in enumerate(slides):
        if i==0:body='<h1>'+html.escape(slide['title'])+'</h1>'+''.join('<p>'+html.escape(line)+'</p>' for line in slide['lines'])
        else:body='<h1>'+html.escape(slide['title'])+'</h1><ul>'+''.join('<li>'+html.escape(line)+'</li>' for line in slide['lines'])+'</ul>'
        sections.append(f'<section class="slide {"cover" if i==0 else ""}" style="background-image:url(assets/{"cover" if i==0 else "inside"}.jpg)">{body}<footer>{html.escape(slide["source"])} · {i+1}/{len(slides)}</footer></section>')
    deck='<!doctype html><html lang="en"><meta charset="utf-8"><title>Udyam Digital business case</title><style>'+style+'</style><body>'+''.join(sections)+'</body></html>'
    (OUT/'business-case.html').write_text(deck,encoding='utf-8')
    svg=architecture();(OUT/'architecture.svg').write_text(svg,encoding='utf-8')
    privacy=(ROOT/'docs/PRIVACY.md').read_text(encoding='utf-8')
    blocks=[]
    for paragraph in privacy.strip().split('\n\n'):
        if paragraph.startswith('# '):blocks.append('<h1>'+html.escape(paragraph[2:])+'</h1>')
        else:blocks.append('<p>'+re.sub(r'\*\*(.*?)\*\*',r'<strong>\1</strong>',html.escape(paragraph))+'</p>')
    privacy_html='<!doctype html><html lang="en"><meta charset="utf-8"><title>Privacy and security design</title><style>@page{size:A4;margin:15mm}body{font:10pt/1.32 Arial;color:#172e29}h1{font-size:18pt;color:#a43425}p{margin:0 0 10pt}</style><body>'+''.join(blocks)+'</body></html>'
    (OUT/'privacy.html').write_text(privacy_html,encoding='utf-8')
    from playwright.sync_api import sync_playwright
    from pypdf import PdfReader
    with sync_playwright() as pw:
        browser=pw.chromium.launch();page=browser.new_page(viewport={'width':1280,'height':720})
        page.goto((OUT/'business-case.html').as_uri());page.pdf(path=str(OUT/'Udyam_Digital_Business_Case_7_Slides.pdf'),prefer_css_page_size=True,print_background=True)
        for index in range(len(slides)):page.locator('.slide').nth(index).screenshot(path=str(OUT/f'assets/slide-{index+1}.png'))
        # Cross-check HTML text boxes for overflow before publishing the artifact.
        assert page.locator('.slide').evaluate_all('(nodes)=>nodes.every(n=>n.scrollHeight<=n.clientHeight && n.scrollWidth<=n.clientWidth)')
        page.goto((OUT/'privacy.html').as_uri());page.pdf(path=str(OUT/'Privacy_and_Security.pdf'),prefer_css_page_size=True,print_background=True)
        page.screenshot(path=str(OUT/'assets/privacy-preview.png'),full_page=True)
        page.set_content('<style>@page{size:16in 8.6in;margin:0}body{margin:0}svg{display:block;width:100%;height:auto}</style>'+svg)
        page.pdf(path=str(OUT/'Architecture.pdf'),prefer_css_page_size=True,print_background=True)
        browser.close()
    assert len(PdfReader(OUT/'Udyam_Digital_Business_Case_7_Slides.pdf').pages)==7
    assert len(PdfReader(OUT/'Privacy_and_Security.pdf').pages)==1
    assert len(PdfReader(OUT/'Architecture.pdf').pages)==1
    (OUT/'build-manifest.json').write_text(json.dumps({'slides':7,'privacy_pages':1,'architecture_pages':1,
        'deck_pptx':'Udyam_Digital_Business_Case_7_Slides.pptx','deck_pdf':'Udyam_Digital_Business_Case_7_Slides.pdf',
        'template':TEMPLATE.name,'status':'Reviewable draft; live-provider validation and final demo recording pending',
        'pricing':{'monthly':1624,'setup':0,'taxes':'excluded'},'sources':['smb_leads.csv','product_catalogue.csv','docs/PRIVACY.md','current application code','docs/SUBMISSION_SOURCES.md']},indent=2),encoding='utf-8')
    print('Built and checked: 7-slide editable PPTX + PDF, one-page privacy PDF and one-page architecture PDF/SVG. Review before submission.')


if __name__=='__main__':main()
