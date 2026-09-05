import json
d = json.load(open('data/pricing.json', encoding='utf-8'))
print('JSON OK | models', len(d['models']), 'plans', len(d['plans']))
mids = {m['id'] for m in d['models']}
bad = [(p['id'], k) for p in d['plans'] for k in p['models'] if k not in mids]
print('unknown refs:', bad or 'none')

og = [p for p in d['plans'] if p['id'] == 'opencode-go'][0]
print('OpenCode Go models:', sorted(og['models'].keys()))
print('  has claude?', 'claude-sonnet-5' in og['models'], '| has gpt-5.6-terra?', 'gpt-5.6-terra' in og['models'])

def blended(p):
    io = 3; ins = io/(io+1); outs = 1/(io+1); miss = ins*0.02; hit = ins*0.98
    return p['input']*miss + p['cachedInput']*hit + p['output']*outs

def eff(pl, mid):
    m = {x['id']: x for x in d['models']}[mid]; e = pl['models'][mid]
    r = pl['monthlyUSD']/e['allowanceUSD']; a = m['api']
    return {'input': a['input']*r, 'cachedInput': a['cachedInput']*r, 'output': a['output']*r}

goat = [p for p in d['plans'] if p['id'] == 'commandcode-goat'][0]
print('--- GOAT ---')
for mid in ['qwen3.8-flash', 'glm-5.3-flash', 'deepseek-v4-flash']:
    e = eff(goat, mid)
    print(f"  {mid}: allow ${goat['models'][mid]['allowanceUSD']} out ${e['output']:.3f}/M blend ${blended(e)*100:.2f}/亿")

ogc = [p for p in d['plans'] if p['id'] == 'opencode-go'][0]
print('--- OpenCode Go ---')
for mid in ['deepseek-v4-flash', 'glm-5.3-flash', 'qwen3.8-flash']:
    e = eff(ogc, mid)
    print(f"  {mid}: allow ${ogc['models'][mid]['allowanceUSD']} out ${e['output']:.3f}/M blend ${blended(e)*100:.2f}/亿")
