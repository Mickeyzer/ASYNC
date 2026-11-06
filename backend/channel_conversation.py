"""Bounded bilingual guided discovery; no provider calls, images or private records."""
from .models import BusinessProfile
from .recommendations import recommend

FIELDS=['business_type','city_tier','employees','sites','monthly_budget','current_internet','gstin_claim','needs']
TYPES=['shop','office','clinic','restaurant','manufacturing','other']
CONNECTIONS=['none','hotspot','broadband','leased_line']
NEEDS=['internet','backup','mobile','whatsapp','email','security','cctv','billing','website','multisite']
QUESTIONS={
 'business_type':('Business type: 1 shop, 2 office, 3 clinic, 4 restaurant, 5 manufacturing, 6 other.', 'व्यवसाय: 1 दुकान, 2 कार्यालय, 3 क्लिनिक, 4 रेस्तराँ, 5 निर्माण, 6 अन्य।'),
 'city_tier':('City tier from the supplied dataset: 1 or 2. Use the web guided form if unsure.', 'दिए गए डेटा में शहर का स्तर: 1 या 2। पता न हो तो वेब फ़ॉर्म देखें।'),
 'employees':('How many employees? Enter a whole number, 1 to 10000.', 'कितने कर्मचारी हैं? 1 से 10000 तक पूर्ण संख्या भेजें।'),
 'sites':('How many locations? Enter 1 to 1000.', 'कितने स्थान हैं? 1 से 1000 तक संख्या भेजें।'),
 'monthly_budget':('Monthly budget in INR? Enter 0 to 10000000; 0 means unspecified.', 'मासिक बजट रुपये में? 0 से 10000000 तक संख्या भेजें। तय न हो तो 0 भेजें।'),
 'current_internet':('Current internet: 1 none, 2 hotspot, 3 broadband, 4 leased line.', 'मौजूदा इंटरनेट: 1 नहीं, 2 हॉटस्पॉट, 3 ब्रॉडबैंड, 4 लीज़्ड लाइन।'),
 'gstin_claim':('Do you have a GSTIN? 1 yes, 2 no, 3 unsure. This is a claim, not verification. Do not send the number.', 'क्या GSTIN है? 1 हाँ, 2 नहीं, 3 पता नहीं। यह केवल दावा है। नंबर न भेजें।'),
 'needs':('Needs: send comma-separated numbers: 1 internet, 2 backup, 3 mobile, 4 WhatsApp, 5 email, 6 security, 7 CCTV, 8 billing, 9 website, 10 multi-site.', 'ज़रूरतें: अल्पविराम से संख्या भेजें: 1 इंटरनेट, 2 बैकअप, 3 मोबाइल, 4 WhatsApp, 5 ईमेल, 6 सुरक्षा, 7 CCTV, 8 बिलिंग, 9 वेबसाइट, 10 कई स्थान।'),
}
NOTICE=('Udyam Digital synthetic demo. Reply START to consent to guided replies and encrypted business answers kept for 30 minutes of inactivity. No Gemini calls. Meta processes messages under its terms. STOP deletes local answers and queued replies. Do not send documents, names or private identifiers. Web help: {url}\n'
        'काल्पनिक डेमो: निर्देशित जवाब और 30 मिनट निष्क्रियता तक एन्क्रिप्टेड उत्तर रखने की अनुमति के लिए START भेजें। Gemini को नहीं भेजा जाता। STOP से स्थानीय उत्तर मिटेंगे। दस्तावेज़ या निजी नंबर न भेजें।')


def step(state,text,url):
    """Return (new state or None, one reply). Text itself is never retained."""
    text=text.strip();command=text.upper();hi=state.get('language')=='hi' if state else False
    if command in ('STOP','बंद'):
        return None,('स्थानीय उत्तर और लंबित जवाब मिटा दिए गए। फिर शुरू करने के लिए नया संदेश भेजें।' if hi else 'Stopped. Local answers and queued replies deleted. Send a new message to begin again.')
    if not state:
        return {'phase':'consent'},NOTICE.format(url=url)
    if command in ('HELP','मदद'):
        return state,('वेब सहायता: ' if hi else 'Web help: ')+url+(' · साइन इन करके सहायता माँगें।' if hi else ' · Sign in to request partner help.')
    if command in ('RESTART','फिर'):
        return {'phase':'consent'},NOTICE.format(url=url)
    if state['phase']=='consent':
        if command not in ('START','शुरू'):return state,NOTICE.format(url=url)
        return {'phase':'language','answers':{}},'Choose language: 1 English, 2 हिन्दी. STOP / बंद cancels.'
    if state['phase']=='language':
        if text not in ('1','2'):return state,'Choose 1 English or 2 हिन्दी.'
        state={**state,'language':'hi' if text=='2' else 'en','phase':FIELDS[0]};hi=text=='2'
        return state,QUESTIONS[FIELDS[0]][int(hi)]
    if state['phase']=='complete':
        return state,('अनुमान वेब फ़ॉर्म में दोहराएँ। दस्तावेज़ जाँच के लिए साइन इन करें: ' if hi else 'Re-enter your reviewed answers on the web and sign in for document checks: ')+url+(' · बदलने के लिए RESTART भेजें।' if hi else ' · Send RESTART to change answers.')
    if state['phase']=='review':
        if command.startswith('EDIT ') and command[5:] in tuple(str(n) for n in range(1,9)):
            state['phase']=FIELDS[int(command[5:])-1];state['editing']=True
            return state,QUESTIONS[state['phase']][int(hi)]
        if command!='CONFIRM':return state,review(state)
        profile=BusinessProfile(**state['answers'],language=state['language'])
        result=recommend(profile,None);quote=result['quote']
        state['phase']='complete'
        if not quote:return state,('बंडल नहीं मिला। वेब फ़ॉर्म में सहायता लें: ' if hi else 'No matching bundle. Use web help: ')+url
        names=', '.join(f"{item['name']} x{item['quantity']} ({item['contract_months']} {'माह अनुबंध' if hi else 'month contract'})" for item in quote['items'])
        total=quote['monthly_total'];setup=quote['setup_total']
        reply=(f'डेमो अनुमान: {names}\nमासिक INR {total}; एक बार सेटअप INR {setup}। कर शामिल नहीं। हर सेवा का न्यूनतम अनुबंध लागू। GSTIN सत्यापित नहीं। यह स्वीकृत ऑर्डर नहीं है। वेब पर शर्तें देखें और दस्तावेज़ जाँच के लिए साइन इन करें: {url}' if hi else
               f'Demo estimate: {names}\nMonthly INR {total}; one-time setup INR {setup}. Taxes excluded. Per-service minimum contracts apply. GSTIN is unverified. This is not an accepted order. Review conditions on the web and sign in for document checks: {url}')
        reasons=list(dict.fromkeys(reason['message_hi' if hi else 'message'] for item in quote['items'] for reason in item['reasons']))
        if reasons:reply+='\n'+('शर्तें: ' if hi else 'Conditions: ')+' '.join(reasons)
        if quote['over_budget_by']:reply+='\n'+('आपके मासिक बजट से अधिक: INR ' if hi else 'Above your monthly budget by INR ')+str(quote['over_budget_by'])
        return state,reply
    field=state['phase']
    try:
        if field=='business_type':value=TYPES[int(text)-1] if text in ('1','2','3','4','5','6') else None
        elif field=='current_internet':value=CONNECTIONS[int(text)-1] if text in ('1','2','3','4') else None
        elif field=='gstin_claim':value=['yes','no','unsure'][int(text)-1] if text in ('1','2','3') else None
        elif field=='needs':
            parts=text.split(',')
            if not 1<=len(parts)<=10 or any(p.strip() not in [str(n) for n in range(1,11)] for p in parts):raise ValueError()
            value=list(dict.fromkeys(NEEDS[int(p.strip())-1] for p in parts))
        else:
            if not text.isascii() or not text.isdigit() or len(text)>8:raise ValueError()
            value=int(text);low,high={'city_tier':(1,2),'employees':(1,10000),'sites':(1,1000),'monthly_budget':(0,10000000)}[field]
            if not low<=value<=high:raise ValueError()
        if value is None:raise ValueError()
    except (ValueError,IndexError):return state,('उत्तर मान्य नहीं है। ' if hi else 'Invalid answer. ')+QUESTIONS[field][int(hi)]
    state['answers'][field]=value
    if state.pop('editing',False) or field==FIELDS[-1]:
        state['phase']='review';return state,review(state)
    state['phase']=FIELDS[FIELDS.index(field)+1]
    return state,QUESTIONS[state['phase']][int(hi)]


def review(state):
    hi=state.get('language')=='hi';answers=state['answers']
    # Numeric choices make the summary reviewable in either language.
    values=[TYPES.index(answers['business_type'])+1,answers['city_tier'],answers['employees'],answers['sites'],answers['monthly_budget'],CONNECTIONS.index(answers['current_internet'])+1,['yes','no','unsure'].index(answers['gstin_claim'])+1,','.join(str(NEEDS.index(n)+1) for n in answers['needs'])]
    names=(['व्यवसाय का विकल्प','शहर का स्तर','कर्मचारी','स्थान','मासिक बजट INR','इंटरनेट का विकल्प','GSTIN का विकल्प','ज़रूरतों के विकल्प'] if hi else ['Business type choice','City tier','Employees','Locations','Monthly budget INR','Internet choice','GSTIN choice','Needs choices'])
    return ('अपने उत्तर जाँचें:\n' if hi else 'Review your answers:\n')+'\n'.join(f'{i+1}. {name}: {value}' for i,(name,value) in enumerate(zip(names,values)))+('\nसही हो तो CONFIRM, बदलने के लिए EDIT 1 से EDIT 8, बंद करने के लिए STOP भेजें।' if hi else '\nReply CONFIRM, EDIT 1 to EDIT 8 to correct a field, or STOP to delete.')
