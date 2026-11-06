"""Explicit, bounded live extraction assessment using student-visible synthetic images."""
import argparse
import json
import sys
import time
import math
from statistics import median
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi import HTTPException
from backend import kyc
from backend.onboarding_models import DocumentDraft

ROOT=Path(__file__).resolve().parents[1]
IMAGES=ROOT/'YTL_TrackA_Udyam_Digital_Data/kyc_documents'


def assess(actual,expected):
    # Report field names/booleans only, never raw identifier values.
    return {name:kyc.normalize(getattr(actual,name))==kyc.normalize(value)
            for name,value in expected.items() if name in DocumentDraft.model_fields}


def summarize_results(output,selected):
    checks=[value for row in output for value in row.get('fields',{}).values()]
    labelled=sum(len(row['expected']) for row in selected)
    latencies=sorted(row['seconds'] for row in output)
    return {'live':True,'attempts':len(output),'successful_documents':sum(row['status']=='extracted' for row in output),
            'labelled_fields':labelled,'assessed_fields':len(checks),'correct_fields':sum(checks),
            'successful_field_accuracy':sum(checks)/len(checks) if checks else None,
            'end_to_end_field_accuracy':sum(checks)/labelled if labelled else None,
            'median_seconds':median(latencies) if latencies else None,
            'p95_seconds':latencies[math.ceil(.95*len(latencies))-1] if latencies else None,'documents':output,
            'limitations':'Student-visible manual labels. Failed requests count as unsuccessful in end-to-end accuracy. No authenticity, identity or decision-accuracy claim.'}


def main():
    parser=argparse.ArgumentParser(description='Assess live extraction without printing extracted document data.')
    parser.add_argument('--prepare',action='store_true',help='Create blank labels from student-visible image filenames; no provider calls.')
    parser.add_argument('--labels',type=Path,default=ROOT/'artifacts/kyc-labels.json')
    parser.add_argument('--consent',action='store_true',help='Explicitly allow sending the selected synthetic images to Gemini.')
    parser.add_argument('--limit',type=int,default=4,choices=range(1,48))
    args=parser.parse_args()
    if args.prepare:
        if args.labels.exists():parser.exit(1,'Labels already exist; no overwrite performed.\n')
        args.labels.parent.mkdir(parents=True,exist_ok=True)
        args.labels.write_text(json.dumps([{'file':p.name,'expected':{}} for p in sorted(IMAGES.glob('*.png'))],indent=2),encoding='utf-8')
        print('Blank labels created. Independently read the original synthetic images and add expected fields before evaluation. Keep labels private.')
        return
    if not args.consent:parser.error('Use --consent only after reviewing which synthetic images will be sent.')
    try:
        labels=json.loads(args.labels.read_text(encoding='utf-8'))
        if not isinstance(labels,list) or any(not isinstance(row,dict) for row in labels):raise ValueError()
    except (OSError,ValueError):parser.error('Labels must be a readable JSON list of image/expected-field objects.')
    selected=[entry for entry in labels if entry.get('expected')][:args.limit]
    if not selected:parser.error('No labelled images. Run --prepare and fill expected fields first.')
    # Validate the entire selected set before any request.
    for entry in selected:
        if not isinstance(entry.get('file'),str):parser.error('Each label needs an image filename.')
        path=IMAGES/entry['file']
        if path.name!=entry['file'] or not path.is_file() or path.suffix.lower()!='.png' or path.resolve().parent!=IMAGES.resolve():
            parser.error('Images must be direct children of the student-visible synthetic document folder.')
        if not isinstance(entry['expected'],dict) or set(entry['expected'])-DocumentDraft.model_fields.keys():
            parser.error('Labels contain an unknown field.')
        if any(value is not None and (not isinstance(value,str) or len(value)>600) for value in entry['expected'].values()):
            parser.error('Expected values must be bounded strings or null for confirmed absence.')
    if len({row['file'] for row in selected})!=len(selected):parser.error('Duplicate images would distort evaluation; select each image once.')
    output=[]
    for entry in selected:
        start=time.monotonic()
        try:
            content=kyc.prepare_image((IMAGES/entry['file']).read_bytes(),'image/png')
            actual=kyc.extract_document(content)
            checks=assess(actual,entry['expected'])
            output.append({'file':entry['file'],'seconds':round(time.monotonic()-start,2),'fields':checks,'status':'extracted'})
        except HTTPException as e:
            code=e.detail.get('code','image_rejected') if isinstance(e.detail,dict) else 'image_rejected'
            output.append({'file':entry['file'],'seconds':round(time.monotonic()-start,2),'status':code})
    result=summarize_results(output,selected)
    destination=ROOT/'artifacts/kyc-evaluation.json'
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
