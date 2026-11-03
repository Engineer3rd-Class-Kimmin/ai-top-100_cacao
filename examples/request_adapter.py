"""Official skill utterance/user separation + observed gateway compatibility.

This module does not extract TC IDs or consultation dates. Unknown metadata and
customer text cannot become an action header or authenticated mall identity.
"""
import hashlib,json,threading,uuid

SKILL_DOCUMENT='https://kakaobusiness.gitbook.io/main/tool/chatbot/skill_guide/answer_json_format'
KNOWN_KEYS=set(('userRequest utterance user id type properties timezone lang block params contexts bot name action clientExtra detailParams value origin callbackUrl callbackToken content timestamp isChannelChatroom botGroupKey botUserKey verifiedConsultation payload signature conversation case_id business_date phone_last4 expires_at revision source testCaseId test_case_id tc_id tcId metadata consultation consultationTime account apiKey api_key token authorization access_token password email phone address').split())
EXPECTED_PATHS=('$.userRequest.utterance','$.userRequest.user.id','$.bot.id','$.content','$.botUserKey','$.botGroupKey',
                '$.testCaseId','$.metadata.tc_id','$.action.clientExtra.testCaseId','$.verifiedConsultation')


def request_shape(payload):
    """Only allowlisted key names, JSON types and presence; never scalar values."""
    rows=[]
    def walk(value,path,depth):
        if len(rows)>=200 or depth>8:return
        typ=('null' if value is None else 'boolean' if isinstance(value,bool) else
             'object' if isinstance(value,dict) else 'array' if isinstance(value,list) else
             'string' if isinstance(value,str) else 'number' if isinstance(value,(int,float)) else 'unsupported')
        rows.append(dict(path=path,type=typ,present=True))
        if isinstance(value,dict):
            # Redact unknown key names too: a malicious key can itself contain PII.
            for key,item in list(value.items())[:80]:walk(item,path+'.'+(key if key in KNOWN_KEYS else '<other>'),depth+1)
        elif isinstance(value,list):
            for item in value[:2]:walk(item,path+'[]',depth+1)
    walk(payload,'$',0)
    paths={row['path'] for row in rows}
    rows.extend(dict(path=path,present=False) for path in EXPECTED_PATHS if path not in paths)
    return dict(schema_version=1,fields=rows)


class RequestDiagnostics:
    def __init__(self,observer):self.observer=observer;self.seen=set();self.lock=threading.Lock()
    def __call__(self,payload):
        record=request_shape(payload)
        fingerprint=hashlib.sha256(json.dumps(record,sort_keys=True).encode()).hexdigest()
        with self.lock:
            if fingerprint in self.seen:return
            if len(self.seen)>=64:return
            self.seen.add(fingerprint)
        try:self.observer(dict(kind='request_shape',schema_sha256=fingerprint,**record))
        except Exception:pass


def normalize_request(payload):
    if not isinstance(payload,dict):raise ValueError('request object required')
    if 'userRequest' not in payload:
        # Actual gateway path is unchanged, including callback expiry timestamps.
        if not all(isinstance(payload.get(k),str) and payload[k] for k in ('botGroupKey','botUserKey')):raise ValueError('gateway identity required')
        if not isinstance(payload.get('content'),str):raise ValueError('gateway text required')
        return dict(payload)
    # Never merge the two identity namespaces or treat action.id as a request ID.
    if any(k in payload for k in ('botGroupKey','botUserKey','content')):raise ValueError('ambiguous request transport')
    request=payload.get('userRequest');bot=payload.get('bot')
    if not isinstance(request,dict) or not isinstance(bot,dict):raise ValueError('skill structure')
    user=request.get('user');utterance=request.get('utterance')
    if not isinstance(user,dict) or not isinstance(utterance,str):raise ValueError('skill text/user')
    if not isinstance(user.get('id'),str) or not user['id'] or not isinstance(bot.get('id'),str) or not bot['id']:raise ValueError('skill identity')
    identity_type=user.get('type','botUserKey')
    if not isinstance(identity_type,str) or not identity_type:raise ValueError('skill identity type')
    scope=hashlib.sha256(json.dumps([bot['id'],identity_type],ensure_ascii=False).encode()).hexdigest()
    event=dict(botGroupKey='skill:'+scope,botUserKey=user['id'],content=utterance,id='skill-event:'+uuid.uuid4().hex)
    # This ID is only an internal event key, never a TC ID or a business timestamp.
    if isinstance(payload.get('verifiedConsultation'),dict):event['verifiedConsultation']=payload['verifiedConsultation']
    return event


def handle_skill_request(service,payload):
    """In-process skill-server entry; does not enable a webhook or change routing."""
    from integrations.kakao.callback import skill_response
    if not isinstance(payload,dict) or 'userRequest' not in payload:
        return skill_response('스킬 요청 형식을 확인하지 못했습니다. 문의 내용을 다시 알려주세요.')
    return skill_response(service.handle(payload))
