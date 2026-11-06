import type {Language} from './types';

const hindi:Record<string,string>={
  consented_records:'सहमति वाले रिकॉर्ड',four_documents_extracted:'चार दस्तावेज़ पढ़े गए',checks_attempted:'जाँच की गई',checks_passed_ever:'कम से कम एक बार जाँच पूरी',orders_created:'ऑर्डर बनाए गए',help_requested_ever:'सहायता माँगी गई',consent_to_four_documents:'सहमति से चार दस्तावेज़ पढ़ने तक',
  customer:'ग्राहक',partner:'पार्टनर',reviewer:'समीक्षक',shop:'दुकान',office:'कार्यालय',clinic:'क्लिनिक',restaurant:'रेस्तराँ',manufacturing:'निर्माण',other:'अन्य',
  documents_pending:'दस्तावेज़ बाकी हैं',action_required:'सुधार आवश्यक',needs_review:'समीक्षा आवश्यक',checks_passed:'डेमो जाँच पूरी',order_created:'डेमो ऑर्डर बनाया गया',accepted:'स्वीकार किया गया',installation_scheduled:'इंस्टॉलेशन तय',activated:'सक्रिय',requested:'अनुरोध किया गया',resolved:'पूरा हुआ',
  documents:'दस्तावेज़',bundle:'बंडल',installation:'इंस्टॉलेशन',
  gst_certificate:'GST प्रमाणपत्र',udyam_certificate:'उद्यम प्रमाणपत्र',signatory_id:'हस्ताक्षरकर्ता पहचान',address_proof:'पते का प्रमाण',
  business_name:'व्यवसाय का नाम',legal_name:'कानूनी नाम',signatory_name:'हस्ताक्षरकर्ता का नाम',address:'पता',city:'शहर',state:'राज्य',registration_date:'पंजीकरण तारीख',issue_date:'जारी करने की तारीख',expiry_date:'समाप्ति तारीख',gstin:'GSTIN',udyam_number:'उद्यम संख्या',id_number:'पहचान संख्या',
  'Follow-up resolved':'सहायता पूरी हुई','Owner requested help':'मालिक ने सहायता माँगी','Document ambiguity needs review':'अस्पष्ट दस्तावेज़ की समीक्षा चाहिए','Document correction needed':'दस्तावेज़ में सुधार चाहिए','Record expires within 12 hours':'रिकॉर्ड 12 घंटे के भीतर समाप्त होगा',
  'Track simulated installation':'डेमो इंस्टॉलेशन देखें','Request corrected documents':'सुधारे हुए दस्तावेज़ माँगें','Review document ambiguity':'दस्तावेज़ की अस्पष्टता जाँचें','Help owner continue':'मालिक को आगे बढ़ने में मदद दें',
  confirm_legibility:'पठनीयता की पुष्टि',request_replacement:'दस्तावेज़ बदलने का अनुरोध',resolve_handoff:'सहायता पूरी की गई',
  record_created:'रिकॉर्ड बनाया गया',record_claimed:'रिकॉर्ड खाते से जोड़ा गया',document_uploaded:'दस्तावेज़ अपलोड किया गया',documents_checked:'दस्तावेज़ जाँचे गए',handoff_requested:'सहायता माँगी गई',handoff_withdrawn:'सहायता की अनुमति वापस ली गई',partner_assigned:'पार्टनर को काम सौंपा गया',handoff_resolved:'सहायता पूरी हुई',replacement_requested:'दस्तावेज़ बदलने को कहा गया',legibility_confirmed:'पठनीयता की पुष्टि हुई',
  'Professional offices':'पेशेवर कार्यालय','Retail shops':'खुदरा दुकानें','Restaurants / cafes':'रेस्तराँ / कैफ़े','Small manufacturers':'छोटे निर्माता',channel_reply_queued:'कतार में रखे WhatsApp जवाब',
  'Micro retail & services':'छोटी दुकानें और सेवाएँ','Small multi-site businesses':'कई स्थानों वाले छोटे व्यवसाय',
  document_received:'दस्तावेज़ मिला',document_replaced:'दस्तावेज़ बदला गया',order_accepted:'डेमो ऑर्डर स्वीकार किया गया',
  retained_records:'मौजूदा रिकॉर्ड',records_with_checks:'जाँच वाले रिकॉर्ड',records_with_passed_checks:'जाँच पार करने वाले रिकॉर्ड',records_with_orders:'ऑर्डर वाले रिकॉर्ड',records_with_handoff:'सहायता वाले रिकॉर्ड',records_with_resolved_handoff:'सहायता पूरी होने वाले रिकॉर्ड',
  consent_to_passed_checks:'सहमति से जाँच पूरी होने तक',consent_to_order:'सहमति से ऑर्डर तक',help_request_to_resolution:'अनुरोध से सहायता पूरी होने तक',
  advisor_request:'सलाहकार अनुरोध',advisor_success:'सलाहकार सफल उत्तर',extraction_request:'पढ़ने का अनुरोध',extraction_success:'सफल दस्तावेज़ पठन',extraction_failure:'असफल दस्तावेज़ पठन',check_passed:'जाँच पूरी',check_blocked:'जाँच रुकी',handoff:'सहायता अनुरोध',rate_limited:'अनुरोध सीमा पूरी',channel_ingress:'WhatsApp प्राप्त संदेश',
  'Professionals':'पेशेवर','Retail':'खुदरा व्यापार','Manufacturing':'निर्माण','Services':'सेवाएँ','Hospitality':'आतिथ्य',
};
export function label(value:string,language:Language){return language==='hi'?(hindi[value]||'अन्य स्थिति'):value.replaceAll('_',' ');}

const errors:Record<string,string>={
  'Your passwords do not match. Enter the same password in both fields.':'दोनों पासवर्ड एक जैसे होने चाहिए। दोनों जगह वही पासवर्ड लिखें।',
  'Username or password incorrect.':'यूज़रनेम या पासवर्ड गलत है।',
  'Current password incorrect.':'मौजूदा पासवर्ड गलत है।',
  'That username is unavailable.':'यह यूज़रनेम उपलब्ध नहीं है।',
  'Sign in to continue.':'आगे बढ़ने के लिए साइन इन करें।',
  'Session not found.':'यह सत्र नहीं मिला या पहले ही समाप्त हो गया।',
  'New passwords do not match.':'नए पासवर्ड मेल नहीं खाते।',
  'This account does not have permission for that action.':'इस खाते को इस कार्रवाई की अनुमति नहीं है।',
  'Evidence or workflow changed. Refresh before deciding.':'जानकारी बदल गई है। निर्णय लेने से पहले फिर लोड करें।',
  'Select an active partner account.':'सक्रिय पार्टनर का खाता चुनें।',
  'The owner has not consented to partner follow-up.':'मालिक ने पार्टनर से संपर्क की अनुमति नहीं दी है।',
  'Extracted evidence expired. Ask the owner to upload and check again.':'निकाली गई जानकारी समाप्त हो गई है। मालिक से फिर अपलोड और जाँच करने को कहें।',
  'Document checks must pass before a demo order can be created.':'डेमो ऑर्डर बनाने से पहले दस्तावेज़ जाँच पूरी करें।',
  'A submitted demo order cannot be edited. Start a new estimate instead.':'भेजे गए डेमो ऑर्डर को बदल नहीं सकते। नया अनुमान बनाएँ।',
  'Resolve catalogue restrictions and missing companion products first.':'पहले सेवा की शर्तें पूरी करें और ज़रूरी साथ वाली सेवाएँ जोड़ें।',
  'The bundle no longer passes catalogue requirements. Start a revised estimate.':'बंडल अब सेवा की शर्तें पूरी नहीं करता। नया अनुमान बनाएँ।',
  'Catalogue prices or terms changed. Start a new estimate and review the changes.':'कीमतें या शर्तें बदल गई हैं। नया अनुमान बनाकर बदलाव जाँचें।',
  'The order status changed or cannot advance. Refresh the tracker.':'ऑर्डर की स्थिति बदल गई है या आगे नहीं बढ़ सकती। ट्रैकर फिर लोड करें।',
  'This draft changed during extraction. Upload one document at a time and retry.':'जानकारी पढ़ते समय मसौदा बदल गया। एक बार में एक दस्तावेज़ अपलोड करें और फिर प्रयास करें।',
  'Only legibility ambiguity can be confirmed, after checking original documents. Other failures need corrected evidence.':'मूल दस्तावेज़ देखने के बाद केवल पठनीयता की पुष्टि कर सकते हैं। अन्य विफलताओं के लिए सही प्रमाण चाहिए।',
  'This record has no consent for document review. Start a new consented check.':'इस रिकॉर्ड की समीक्षा की अनुमति नहीं है। नई अनुमति के साथ जाँच शुरू करें।',
  'Review history is full. Start a new record rather than losing decision history.':'समीक्षा इतिहास भर गया है। पुराना इतिहास मिटाने के बजाय नया रिकॉर्ड बनाएँ।',
  'No active handoff.':'सहायता का कोई सक्रिय अनुरोध नहीं है।',
  'Partners cannot approve or review documents.':'पार्टनर दस्तावेज़ की समीक्षा या स्वीकृति नहीं दे सकते।',
  'GSTIN verification expired or is invalid. Verify again.':'GSTIN जाँच समाप्त या अमान्य है। फिर जाँच करें।',
  'Enter a valid synthetic GSTIN, including its checksum.':'सही चेकसम वाला काल्पनिक GSTIN भरें।',
  'Use an image no larger than 5 MB.':'अधिकतम 5 MB की तस्वीर चुनें।',
  'Upload a PNG or JPEG image.':'PNG या JPEG तस्वीर अपलोड करें।',
  'Please check the supplied fields.':'भरे गए उत्तर जाँचें और फिर प्रयास करें।',
};
export function localError(message:string,language:Language,status?:number){
  if(language!=='hi'||/[\u0900-\u097f]/.test(message))return message;
  if(errors[message])return errors[message];
  if(status===429||/busy|Too many|capacity/.test(message))return 'अनुरोध सीमा पूरी है। थोड़ा रुककर फिर प्रयास करें।';
  if(status===404||/not found|expired/.test(message))return 'रिकॉर्ड नहीं मिला या समाप्त हो गया। जानकारी जाँचकर फिर खोलें।';
  if(status===409)return 'रिकॉर्ड या आवश्यक शर्तें बदल गई हैं। फिर लोड करें और बताई गई जाँच पूरी करें।';
  if(status===503||/storage|unavailable|network|fetch/i.test(message))return 'सेवा अभी उपलब्ध नहीं है। कनेक्शन जाँचकर फिर प्रयास करें।';
  return 'अनुरोध पूरा नहीं हुआ। भरी गई जानकारी और अनुमति जाँचकर फिर प्रयास करें।';
}
export const currentLanguage=():Language=>document.documentElement.lang==='hi'?'hi':'en';
