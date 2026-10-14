import json,subprocess,glob,re
import os
HERE=os.path.dirname(os.path.abspath(__file__))
root=os.path.join(HERE,'..','..','static','js')+'/'
# old EN dict
old=json.loads(subprocess.check_output(['node','-e',"""
global.OBB={DICT:{}};require('fs');eval(require('fs').readFileSync('static/js/i18n-en.js','utf8').replace('OBB.DICT.en','OBB.DICT.en'));
console.log(JSON.stringify(OBB.DICT.en))""",root+'i18n-en.js']))
old={re.sub(r'\s+',' ',k.strip()):v for k,v in old.items()}
old.pop('Vence {}OCT{} · OI {} · Vol/OI {}',None)
en,pt=dict(old),{}
for ln in open(os.path.join(HERE,'fuentes','p0pt.txt'),encoding='utf8'):
    ln=ln.rstrip('\n')
    if not ln.strip(): continue
    es,p=ln.split(' ||| ')
    pt[es.strip()]=p.strip()
for fn in sorted(glob.glob(os.path.join(HERE,'fuentes','p[0-9].txt')))+sorted(glob.glob(os.path.join(HERE,'fuentes','q*.txt')))+sorted(glob.glob(os.path.join(HERE,'fuentes','r*.txt'))):
    for ln in open(fn,encoding='utf8'):
        ln=ln.rstrip('\n')
        if not ln.strip(): continue
        parts=ln.split(' ||| ')
        if len(parts)!=3: print('BAD',fn,ln[:80]); continue
        es,e,p=[re.sub(r'\s+',' ',x.strip()) for x in parts]
        en[es]=e; pt[es]=p
# parity
for k in en:
    if k not in pt: print('NO PT',k[:70])
for k in pt:
    if k not in en: print('NO EN',k[:70])
    else:
        a,b,c=k.count('{}'),en[k].count('{}'),pt[k].count('{}')
        if not(a==b==c): print('PLACEHOLDERS',k[:60],a,b,c)
hdr=lambda n,l:f"/* Diccionario {n} (clave = texto exacto en español; las cifras se escriben como {{}}). Lo que no esté aquí se muestra en español. Generado: no editar a mano, ver tools/ */\nOBB.DICT.{l} = "
open(root+'i18n-en.js','w',encoding='utf8').write(hdr('inglés','en')+json.dumps(en,ensure_ascii=False,indent=0)+';\n')
open(root+'i18n-pt.js','w',encoding='utf8').write(hdr('portugués (Brasil)','pt')+json.dumps(pt,ensure_ascii=False,indent=0)+';\n')
print(len(en),len(pt))
