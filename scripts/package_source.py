"""Prepare a clean source archive with an explicit allowlist, without publishing it."""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'submission'
FILES=('README.md','requirements.txt','requirements-dev.txt','pytest.ini','run.cmd','check_gemini.py',
       'Dockerfile','compose.yaml','.dockerignore','.gitignore','.gitattributes','.env.example')
DIRECTORIES={'backend':{'.py'},'scripts':{'.py','.cjs'},'tests':{'.py'},'docs':{'.md'},
             'frontend/src':{'.tsx','.ts'},'frontend/public':{'.svg'},'.github/workflows':{'.yml'}}
FRONTEND=('frontend/package.json','frontend/package-lock.json','frontend/tsconfig.json','frontend/vite.config.ts','frontend/styles.css','frontend/index.html')
DATA=('README.md','product_catalogue.csv','smb_leads.csv','mock_gstin_registry.csv','mock_udyam_registry.csv')
DEMO_FILES=('README.md','manifest.json','DEMO01_gst_certificate.png','DEMO01_udyam_certificate.png','DEMO01_signatory_id.png','DEMO01_address_proof.png')


def inputs():
    paths={ROOT/name for name in FILES+FRONTEND}
    for directory,suffixes in DIRECTORIES.items():
        paths.update(p for p in (ROOT/directory).rglob('*') if p.is_file() and p.suffix in suffixes and '__pycache__' not in p.parts)
    data=ROOT/'YTL_TrackA_Udyam_Digital_Data'
    paths.update(data/name for name in DATA)
    paths.update((data/'kyc_documents').glob('K[0-9][0-9]_*.png'))
    paths.update(ROOT/'6ad9d4887d445_airtel_sync'/name for name in ('Airtel_SYNC_Case.pdf','Submission Template_Sync.pptx'))
    paths.update(OUT/name for name in ('README.md','demo-narration.md'))
    paths.update(ROOT/'demo_documents/checkout'/name for name in DEMO_FILES)
    for path in sorted(paths):
        if not path.is_file() or path.resolve()!=path.absolute() or not path.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError('Source package input missing or linked outside its expected location.')
        yield path.relative_to(ROOT).as_posix(),path


def main():
    OUT.mkdir(exist_ok=True);manifest={}
    with ZipFile(OUT/'Udyam_Digital_Source.zip','w',ZIP_DEFLATED) as archive:
        for name,path in inputs():
            data=path.read_bytes();archive.writestr(name,data)
            manifest[name]=hashlib.sha256(data).hexdigest()
        archive.writestr('PACKAGE_MANIFEST.json',json.dumps(manifest,indent=2))
    (OUT/'source-manifest.json').write_text(json.dumps({'files':len(manifest),'sha256':hashlib.sha256((OUT/'Udyam_Digital_Source.zip').read_bytes()).hexdigest(),
        'scope':'Explicit source/student-data allowlist. No credentials, runtime records, caches, learning notes or judges-only data. Not published.'},indent=2),encoding='utf-8')
    print(f'Prepared clean source archive: {len(manifest)} files. Nothing published or committed.')


if __name__=='__main__':main()
