"""Build a reviewable deck and PDFs from supplied branding and reproducible evidence."""
import base64
import copy
import html
import json
import re
import hashlib
import shutil
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
FINAL_BASENAME='Spicers_TIET'
TEAM='Spicers | TIET'
MEMBERS='Ishan Bhat | Gaurav Prakash Srivastava'
LINKS=[('Watch demo', 'https://youtu.be/VdtKxBKpCHQ'),
       ('Code repository', 'https://github.com/Mickeyzer/ASYNC')]
SUPPORTING_LINKS=[
    ('Full architecture (PDF)', 'https://github.com/Mickeyzer/ASYNC/blob/main/submission/final/Architecture.pdf'),
    ('Privacy and security note (PDF)', 'https://github.com/Mickeyzer/ASYNC/blob/main/submission/final/Privacy_and_Security.pdf')]
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
        'Enterprise Track A | Accel Business prototype',TEAM,MEMBERS],
       'source':'Working local prototype. Payments, availability and activation are simulated.'},
      {'title':'Start where quote drop-off hurts','lines':[
        f"Only {evidence['activated']} of {evidence['leads']:,} supplied leads activated ({evidence['activation_rate']:.2%}).",
        'Needs assessed: 1,974; quotes accepted: 861. Only 43.6% make that transition.',
        f"Priority segment: professional offices, {professional['leads']:,} leads and {professional['activation_rate']:.2%} historical activation.",
        'Clinics, CA firms and coaching centres: dependable internet, email and basic security.',
        'Value: an understandable bundle, visible fees, fewer document hand-offs and a saved status view.'],
       'source':'Source: supplied synthetic leads and brief. Segment priority is a proposed pilot choice, not proven optimal.'},
      {'title':'Compete on the complete journey','lines':[
        'Udyam: reviewed Hindi/English discovery -> editable quote -> mock KYC -> saved tracker.',
        'Pilot hypothesis: fewer owner hand-offs, with consented partner help for exceptions.'],
       'comparison':[
         ['Comparator','Observed strength / case baseline','Our response for the pilot'],
         ['JioBusiness Solution','Integrated connectivity, voice and digital services. Bundles already exist.','Compete on journey completion; do not claim bundling is new or cheaper.'],
         ['Vi ReadyForNext','Digital-readiness assessment, tailored report and service offers. Advice already exists.','Carry reviewed needs into a catalogue quote and document checklist.'],
         ['Case baseline','Field-led discovery, 3-5-day quotes and documents collected across channels.','Editable instant estimate, consented checks and one saved status view.']],
       'source':'Official JioBusiness / Vi pages, checked 8 Nov 2026; case brief. No full competitor-flow audit or price comparison.'},
      {'title':'From business needs to an editable quote','lines':[
        'Create an account; use English/Hindi, typed needs or consented voice. Review the advisor draft.',
        'Tier-1 clinic, five staff: Biz Fibre 100 at INR 999 + five email seats at INR 125 each.',
        f"Monthly: INR {estimate['monthly_total']:,}. Setup: INR {estimate['setup_total']:,}. First month: INR {estimate['first_month_estimate']:,}. Taxes excluded.",
        'Backend catalogue rules control eligibility, dependencies and prices. Edit quantities and add-ons; 12-month contracts.',
        'Review estimate, consent to four-document checks, then create and track a simulated order.'],
       'source':'Source: catalogue/quote code at build time. Starter bundle, not a budget optimizer or real commercial offer.'},
      {'title':'Rules, privacy and people protect trust','lines':[
        'React -> FastAPI -> catalogue/mock registries + SQLite. Consented Gemini drafts require review.',
        'Separate consents for drafting, speech, documents and partner contact; app does not persist uploaded images.',
        'Raw fields expire after 30 minutes or order submission; masked journey records after 24 hours.',
        'Account ownership and staff roles limit access. Partners see assigned, consented summaries only.',
        'Original inspection can resolve legibility; missing, expired or inconsistent evidence still blocks.'],
       'links':SUPPORTING_LINKS,
       'source':'Open the full supporting PDFs above. Mock checks use 15 July 2026; not compliance certification.'},
      {'title':'Rollout gates and risks','lines':[
        'Now: working synthetic prototype and recorded demo; hosted CI covers API, browser and artifact checks.',
        'Provider risk: guided fallback during outages; live extraction and microphone quality need broader evaluation.',
        'Deployment gate: validate Docker, managed identity, encrypted hosting and operating controls before a pilot.',
        'Delivery risk: real availability, payment and provisioning need integrations; current stages are simulated.',
        'Next: invited professional-office pilot with partner support and a comparable baseline; WhatsApp stays disabled.'],
       'source':'Demo uses separately labelled DEMO01 synthetic documents; original specimens remain unchanged. No production-readiness claim.'},
      {'title':'Five proposed targets, not claimed results','lines':[
        'Lead-to-activation: historical 7.36%; proposed comparable-cohort target 10%.',
        'Mean lead-to-activation: 17.62 days; proposed target at most 12 days.',
        'Blended acquisition cost: INR 15,053; proposed target at most INR 12,000.',
        'Six-month churn: 15.22%; proposed target at most 12%. Status chases: about 3 to at most 1.',
        'At fixed acquisition spend only, 7.36% to 10% conversion implies about INR 11,079 CAC.'],
       'source':'Scenario arithmetic, not measured savings. Segment pilots need their own comparable baseline; churn needs six months.'},
    ]


def textbox(identifier,x,y,w,h,paragraphs,size=1600,color='172A29',bold=False,link_id=None):
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
        if link_id:
            ET.SubElement(rp,f"{{{ns['a']}}}hlinkClick",{f"{{{ns['r']}}}id":link_id})
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
            tree.append(textbox(1001,.6,3.02,5.0,.6,[data['title']],3200,'FFFFFF',True))
            tree.append(textbox(1002,.6,3.66,6.0,1.25,data['lines'],1300,'FFFFFF'))
            for number,(label,url) in enumerate(LINKS):
                tree.append(textbox(1010+number,.6+number*1.65,5.02,1.6,.3,[label],1250,'FFFFFF',True,link_id=f'rIdSubmission{number}'))
        else:
            tree.append(textbox(1001,.58,1.0,8.85,.75,[data['title']],2500,'BA261B',True))
            if 'comparison' in data:
                for row,cells in enumerate(data['comparison']):
                    for column,(x,width) in enumerate(((.65,1.45),(2.22,3.25),(5.65,3.55))):
                        tree.append(textbox(1100+row*3+column,x,1.87+row*.56,width,.55,[cells[column]],1050 if row else 1100,'172A29' if row else 'BA261B',row==0))
                tree.append(textbox(1002,.65,4.18,8.68,.65,data['lines'],1100))
            else:
                tree.append(textbox(1002,.65,1.88,8.68,2.95,['• '+line for line in data['lines']],1500))
            tree.append(textbox(1003,.65,4.9,8.0,.4,[data['source']],800,'596764'))
            for number,(label,_) in enumerate(data.get('links',[])):
                tree.append(textbox(1020+number,.65+number*3.1,4.53,3.0,.28,[label],1150,'BA261B',True,link_id=f'rIdSupporting{number}'))
        slide_rels=ET.fromstring(files[f'ppt/slides/_rels/slide{template}.xml.rels'])
        for rel in list(slide_rels):
            if rel.get('Type','').endswith('/notesSlide'):slide_rels.remove(rel)
        if index==1:
            for number,(_,url) in enumerate(LINKS):
                ET.SubElement(slide_rels,f"{{{NS['rel']}}}Relationship",Id=f'rIdSubmission{number}',Type=NS['r']+'/hyperlink',Target=url,TargetMode='External')
        for number,(_,url) in enumerate(data.get('links',[])):
            ET.SubElement(slide_rels,f"{{{NS['rel']}}}Relationship",Id=f'rIdSupporting{number}',Type=NS['r']+'/hyperlink',Target=url,TargetMode='External')
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
    outputs['docProps/core.xml']=b'''<?xml version="1.0" encoding="UTF-8"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Spicers TIET - Udyam Digital</dc:title><dc:creator>Ishan Bhat; Gaurav Prakash Srivastava</dc:creator><dc:description>Seven-slide synthetic-data prototype business case and proposed rollout.</dc:description></cp:coreProperties>'''
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
    from scripts.architecture_diagram import render_architecture
    return render_architecture()


def final_package():
    destination=OUT/'final';destination.mkdir(exist_ok=True)
    files={f'{FINAL_BASENAME}.pptx':'Udyam_Digital_Business_Case_7_Slides.pptx',
           f'{FINAL_BASENAME}.pdf':'Udyam_Digital_Business_Case_7_Slides.pdf',
           'Architecture.pdf':'Architecture.pdf','Privacy_and_Security.pdf':'Privacy_and_Security.pdf'}
    manifest={'team':'Spicers','campus':'TIET','members':['Ishan Bhat','Gaurav Prakash Srivastava'],
              'video_url':LINKS[0][1],'repository_url':LINKS[1][1],
              'supporting_document_urls':dict(SUPPORTING_LINKS),
              'maximum_file_bytes':20_000_000,'slides_including_cover':7,'files':{}}
    for name,source in files.items():
        target=destination/name;shutil.copyfile(OUT/source,target)
        payload=target.read_bytes()
        assert len(payload)<manifest['maximum_file_bytes'],f'{name} exceeds the 20 MB limit'
        manifest['files'][name]={'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}
    (destination/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    (destination/'README.md').write_text(f'''# Spicers | TIET submission files

Ishan Bhat and Gaurav Prakash Srivastava

Upload **{FINAL_BASENAME}.pdf** and **{FINAL_BASENAME}.pptx** in the two slide-upload fields shown by the portal. Each has seven slides including the cover and is below the reported 20 MB limit. Both contain clickable video and repository links on the cover, plus direct architecture/privacy PDF links on slide 5. The supporting PDFs remain separate files in this repository; no extra slides have been appended. This packages the brief's supporting deliverables for access through the available fields, without claiming an organizer-approved exception.

- [Recorded demo]({LINKS[0][1]})
- [Source repository]({LINKS[1][1]})
- [Full architecture PDF]({SUPPORTING_LINKS[0][1]})
- [One-page privacy/security note]({SUPPORTING_LINKS[1][1]})

The repository is private; arrange authorized judge access before submitting its link. The final video was supplied by the team; it is separate from the controlled demo-rehearsal.webm. Automated playback and duration inspection were unavailable. The brief caps the video at three minutes.

The demo uses separately labelled synthetic DEMO01 documents and simulated payment, availability and activation. Business targets are proposed, not measured uplift. No portal submission has been performed by these build scripts. Check the logged-in round, review the files, submit personally and retain confirmation.
''',encoding='utf-8')


def main():
    OUT.mkdir(exist_ok=True);(OUT/'assets').mkdir(exist_ok=True)
    slides=content();pptx(slides)
    with ZipFile(TEMPLATE) as source:
        cover=source.read('ppt/media/image2.jpg');inside=source.read('ppt/media/image1.jpg')
    for name,data in [('cover.jpg',cover),('inside.jpg',inside)]: (OUT/'assets'/name).write_bytes(data)
    style='''@page{size:13.333333in 7.5in;margin:0}*{box-sizing:border-box}body{margin:0;font-family:Arial,sans-serif;color:#173e37}.slide{width:1280px;height:720px;position:relative;break-after:page;background-size:cover;padding:125px 78px 70px;overflow:hidden}.slide:last-child{break-after:auto}h1{font-size:36px;color:#ba261b;line-height:1.13;margin:0 0 34px}li{font-size:23px;line-height:1.38;margin:0 0 19px}ul{padding-left:24px}footer{position:absolute;bottom:50px;left:83px;width:1050px;font-size:13px;color:#596764}.cover{padding:415px 72px 40px;color:white}.cover h1{font-size:48px;color:white;margin-bottom:12px}.cover p{font-size:22px;max-width:590px;margin:8px 0}.cover footer{display:none}'''
    style+='''.cover{padding-top:385px}.cover p{font-size:21px;max-width:760px;margin:8px 0}.cover .links{margin-top:16px;display:flex;gap:30px}.cover a{color:white;font-size:20px;font-weight:bold;text-decoration:underline}table{border-collapse:collapse;width:100%;table-layout:fixed;margin:0 0 14px;font-size:18px;line-height:1.3}th,td{vertical-align:top;text-align:left;padding:12px 15px;border-bottom:1px solid #c9d3d0}th{color:#9f211b;background:#f4e9e7}th:first-child{width:18%}th:nth-child(2){width:39%}.comparison h1{margin-bottom:23px}.comparison li{font-size:19px;margin-bottom:10px}.comparison ul{margin-top:14px}'''
    style+='''.supporting-links{position:absolute;left:83px;bottom:93px;display:flex;gap:34px;font-size:18px;font-weight:bold}.supporting-links a{color:#9f211b;text-decoration:underline}'''
    sections=[]
    for i,slide in enumerate(slides):
        if i==0:
            body='<h1>'+html.escape(slide['title'])+'</h1>'+''.join('<p>'+html.escape(line)+'</p>' for line in slide['lines'])
            body+='<div class="links">'+''.join(f'<a href="{html.escape(url)}">{html.escape(label)}</a>' for label,url in LINKS)+'</div>'
        else:
            body='<h1>'+html.escape(slide['title'])+'</h1>'
            if 'comparison' in slide:
                body+='<table>'+''.join('<tr>'+''.join(f'<{"th" if row==0 else "td"}>{html.escape(cell)}</{"th" if row==0 else "td"}>' for cell in cells)+'</tr>' for row,cells in enumerate(slide['comparison']))+'</table>'
            body+='<ul>'+''.join('<li>'+html.escape(line)+'</li>' for line in slide['lines'])+'</ul>'
            if slide.get('links'):
                body+='<div class="supporting-links">'+''.join(f'<a href="{html.escape(url)}">{html.escape(label)}</a>' for label,url in slide['links'])+'</div>'
        sections.append(f'<section class="slide {"cover" if i==0 else "comparison" if "comparison" in slide else ""}" style="background-image:url(assets/{"cover" if i==0 else "inside"}.jpg)">{body}<footer>{html.escape(slide["source"])} · {i+1}/{len(slides)}</footer></section>')
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
        browser.close()
    from scripts.architecture_diagram import write_architecture
    write_architecture(OUT)
    assert len(PdfReader(OUT/'Udyam_Digital_Business_Case_7_Slides.pdf').pages)==7
    assert len(PdfReader(OUT/'Privacy_and_Security.pdf').pages)==1
    assert len(PdfReader(OUT/'Architecture.pdf').pages)==1
    final_package()
    (OUT/'build-manifest.json').write_text(json.dumps({'slides':7,'privacy_pages':1,'architecture_pages':1,
        'deck_pptx':'Udyam_Digital_Business_Case_7_Slides.pptx','deck_pdf':'Udyam_Digital_Business_Case_7_Slides.pdf',
        'template':TEMPLATE.name,'status':'Final team-named artifacts built; video linked; user portal submission pending',
        'final_directory':'final','final_basename':FINAL_BASENAME,'video_url':LINKS[0][1],'repository_url':LINKS[1][1],
        'pricing':{'monthly':1624,'setup':0,'taxes':'excluded'},'sources':['smb_leads.csv','product_catalogue.csv','docs/PRIVACY.md','current application code','docs/SUBMISSION_SOURCES.md']},indent=2),encoding='utf-8')
    print('Built and checked: 7-slide editable PPTX + PDF, one-page privacy PDF and one-page architecture PDF/SVG. Review before submission.')


if __name__=='__main__':main()
