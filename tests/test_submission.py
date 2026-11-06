"""Independent checks of required deliverable limits and package consistency."""
import csv
import posixpath
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile
import hashlib
import json

from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'submission'


def test_presentation_is_editable_ten_slides_and_all_internal_links_resolve():
    with ZipFile(OUT/'Udyam_Digital_Business_Case.pptx') as archive:
        names=set(archive.namelist())
        presentation=ET.fromstring(archive.read('ppt/presentation.xml'))
        p='http://schemas.openxmlformats.org/presentationml/2006/main'
        assert len(presentation.find('{'+p+'}sldIdLst'))==10
        text=[]
        for index in range(1,11):
            slide=ET.fromstring(archive.read(f'ppt/slides/slide{index}.xml'))
            text.extend(n.text or '' for n in slide.iter() if n.tag.endswith('}t'))
        assert len(text)>60  # Editable text, not just a raster deck.
        for name in names:
            if not name.endswith('.rels'):continue
            # Derive the source part independently of the artifact writer.
            if name=='_rels/.rels':base=''
            else:base=posixpath.dirname(name.replace('/_rels/','/').removesuffix('.rels'))
            for relationship in ET.fromstring(archive.read(name)):
                if relationship.get('TargetMode')=='External':continue
                target=relationship.get('Target','')
                resolved=posixpath.normpath(posixpath.join(base,target)).lstrip('/')
                assert resolved in names,(name,target,resolved)
        assert 'not claimed results' in ' '.join(text)


def test_pdf_page_limits_and_source_numbers_are_independently_checked():
    deck=PdfReader(OUT/'Udyam_Digital_Business_Case.pdf')
    privacy=PdfReader(OUT/'Privacy_and_Security.pdf')
    assert len(deck.pages)==10 and len(privacy.pages)==1
    assert len(PdfReader(OUT/'Architecture.pdf').pages)==1
    with (ROOT/'YTL_TrackA_Udyam_Digital_Data/smb_leads.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    active=[r for r in rows if r['outcome']=='Activated']
    activation=f'{len(active)/len(rows):.2%}'
    churn=f"{sum(r['churned_within_6_months']=='Y' for r in active)/len(active):.2%}"
    text=' '.join(p.extract_text() for p in deck.pages)
    assert activation in text and churn in text
    with (ROOT/'YTL_TrackA_Udyam_Digital_Data/product_catalogue.csv').open(encoding='utf-8-sig',newline='') as f:products={r['product_id']:r for r in csv.DictReader(f)}
    total=int(products['P01']['price_min_inr_per_month'])+5*int(products['P16']['price_min_inr_per_month'])
    assert f'INR {total:,}' in text
    assert 'not measured savings' in text
    assert 'not compliance certification' in privacy.pages[0].extract_text()


def test_source_archive_contains_required_code_and_no_private_runtime_material():
    with ZipFile(OUT/'Udyam_Digital_Source.zip') as archive:
        names=set(archive.namelist())
        for required in ('backend/main.py','frontend/src/App.tsx','scripts/build_submission.py',
                         'requirements.txt','.env.example','YTL_TrackA_Udyam_Digital_Data/product_catalogue.csv'):
            assert required in names
        forbidden=('runtime/','artifacts/','.vibe-wise/','.agents/','.codex/','frontend/node_modules/','.npm-cache/')
        assert not any(name.startswith(forbidden) or 'Judges' in name or name=='.env' for name in names)
        assert sum(name.startswith('YTL_TrackA_Udyam_Digital_Data/kyc_documents/') for name in names)==47
        manifest=json.loads(archive.read('PACKAGE_MANIFEST.json'))
        assert set(manifest)==names-{'PACKAGE_MANIFEST.json'}
        assert all(hashlib.sha256(archive.read(name)).hexdigest()==digest for name,digest in manifest.items())
