# Graphics fidelity ladder (GAME_ROADMAP.md, "Fidelity ladder"): stage 0 = LOD 2 at the start,
# stage 1 = LOD 1 after the Mecha Breacher, stages 2-3 for the next upgrades (3 = max graphics); full detail uses r.DetailMode 3 (Epic), the editor's own level.
import json,sys
sys.path.insert(0,'Tools')
exec(open('/var/home/precosmos/.var/app/com.anthropic.Claude/cache/claude-1000/-var-home-precosmos---------Unreal-Projects-Physis/026d8109-8776-4ded-89bb-41a9dbddde52/scratchpad/combat.py').read().split("ANIM=")[0])
var(P,'FidelityApplied','int');var(P,'MaxHealth','float')
shell(P,'PhysisFidelityApply',[('Stage','int')]);shell(P,'PhysisFidelity');shell(P,'PhysisFidelityReset')
# PhysisFidelityApply (the ladder's console values) and PhysisFidelityReset moved to quality.py, which runs
# right after this script and also locks the pause menu's Quality levels to the stages: edit them there.
# The stage this save has earned. Overridden by Tools/blueprint_logic/center_overrides.py (part progress), run last.
fn(P,'PhysisFidelity',"""(fn PhysisFidelity ()
  (Variables|Default|SetMaxHealth (select (Utilities|String|Contains :SearchIn (Variables|Default|GetFlags) :Substring ",lifeaug,") 20.0 10.0))
  (bind want (select (Utilities|String|Contains :SearchIn (Variables|Default|GetFlags) :Substring ",boss,") 1 0))
  (if (not (== (+ want 1) (Variables|Default|GetFidelityApplied)))
    (Variables|Default|SetFidelityApplied (+ want 1))
    (CallFunction|PhysisFidelityApply :Stage want)))""")
comp(P)
G={'refPath':P+':EventGraph'}
def j(tool,args):
    r=call(tool,args)
    return json.loads(r)['returnValue'] if r else None
end=j('add_event',{'blueprint':{'refPath':P},'event_name':'ReceiveEndPlay','position':{'x':-400,'y':7800}})
out=next(p for p in j('get_node_infos',{'nodes':[end]})[0]['output_pins'] if p['name'] in ('then','execute','Then'))
if not out.get('connected_pins'):
    reset=j('create_node',{'graph':G,'type_id':'CallFunction|PhysisFidelityReset','pos':{'x':0,'y':7800}})
    entry=next(p for p in j('get_node_infos',{'nodes':[reset]})[0]['input_pins'] if p['name']=='execute')
    call('connect_pins',{'output_pin':out['pin_id'],'input_pin':entry['pin_id']})
    print('wired EndPlay reset')
comp(P)
