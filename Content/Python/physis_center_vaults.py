"""The Center's ability vaults: fifteen sealed puzzles, harder than the open puzzles, each holding an augmentation.

Every vault needs abilities from every phase of the game: the station's blade or sidearm (crystal locks low or
high, guardians), the Scan Visor (its stele says in full what to do), the Center's Settle (thorn gates, wounds),
and at least one ability from a later level, so each one waits, visibly, until Physis returns:

  lock kind   actor                         opened by                     token
  thorn       BP_SettleBarrier              Settle                        ,settle,
  light       BP_AbilitySocket GateLight    Light Step (timed, 3 s)       ,lightstep,
  field       BP_AbilitySocket GateDissonance  Dissonance (held 8 s)     ,dissonance,
  grief       BP_AbilitySocket GateMemory   Sit With (for good)           ,sitwith,
  node        BP_AbilitySocket NodeResonance  Resonance Link (raises bridges)  ,resonance,
  anchor      BP_AbilitySocket AnchorReweave  Reweave (rebuilds ramps)    ,reweave,
  echo        BP_AbilitySocket EchoTrace    Trace Reading (reveals stairs) ,trace,
  locks       static BP_TrainingDrone crystals in a room + BP_Encounter (rooms 301+)
  guards      enemies in a room + BP_Encounter

A later ability only has to call BP_Physis.PhysisUsedAbility with its token when used (Settle already does).
Each vault's stages give ,vNN_<stage>, tokens; BP_Requirement joins them into ,vNN_open,, which raises the dais
under the augmentation, a BP_Relic shown from the start (Tease) but taken only once the vault is open.
Augmentation tokens and effects: center_overrides.py AUGMENTS. Texts: physis_center_lore.py VAULT_SCANS.
Walls are 6.6 m HumanWall segments sunk 1.5 m; mesas are SM_CA_Platform blocks with sheer sides; created
stairs rise 105 cm a step, 4.5 m apart (Physis jumps about 150 cm).
"""
import math

import unreal

from physis_center_lore import AUG_SCANS, CENTER_SCANS, GATE_SCANS, VAULT_SCANS

ABILITY = {'light': ',lightstep,', 'field': ',dissonance,', 'grief': ',sitwith,', 'node': ',resonance,', 'anchor': ',reweave,', 'echo': ',trace,'}
MESH = {'light': 'SM_CA_GateLight', 'field': 'SM_CA_GateDissonance', 'grief': 'SM_CA_GateMemory',
        'node': 'SM_CA_NodeResonance', 'anchor': 'SM_CA_AnchorReweave', 'echo': 'SM_CA_EchoTrace'}
TITLE = {'light': 'Light Lattice', 'field': 'Dissonance Field', 'grief': 'Door of Grief', 'node': 'Resonance Node',
         'anchor': 'Reweave Anchor', 'echo': 'Trace Echo', 'lock': 'Crystal Lock', 'prism': 'Light Prism', 'thorn': 'Thorn Barrier'}
HOLD = {'light': 3.0, 'field': 8.0, 'grief': 0.0}
GLOW = {'light': (1, .75, .3), 'field': (.7, .35, 1), 'grief': (.35, .55, 1), 'node': (.3, .9, 1), 'anchor': (.35, 1, .45), 'echo': (1, .6, .2)}
USED = {'light': 'The lattice parts for a few breaths.', 'field': 'Dissonance holds the field open. Quickly.',
        'grief': 'Physis sits with it, and the door opens.', 'node': 'The node sings, and what it was joined to answers.',
        'anchor': 'The anchor remembers, and what was broken is rewoven.', 'echo': 'The past grows solid enough to walk on.'}
AUG = {'hp': ('Health Augmentation', 'SM_CA_AugHealth', (1, .35, .5),
              'Health Augmentation absorbed. Physis gains a Health Tank: ten more health, and she is whole again.'),
       'katana': ('Katana Augmentation', 'SM_CA_AugKatana', (1, .4, .4), 'Katana Augmentation absorbed. Every cut of her blade strikes a quarter harder.'),
       'pistol': ('Pistol Augmentation', 'SM_CA_AugPistol', (1, .6, .2), 'Pistol Augmentation absorbed. Every shot of her sidearm strikes almost a third harder.'),
       'defense': ('Defense Augmentation', 'SM_CA_AugDefense', (.35, .55, 1), 'Defense Augmentation absorbed. Every hit she takes costs fifteen percent less.'),
       'agility': ('Agility Augmentation', 'SM_CA_AugAgility', (.5, 1, .55),
                   'Agility Augmentation absorbed. Her perfect parry opens a tenth of a second longer.')}
LOCKED = 'The vault still holds it. Read the stele at its entrance.'


def entry(title):
    return next(row[:3] for row in VAULT_SCANS + GATE_SCANS + AUG_SCANS + CENTER_SCANS if row[1] == title)


class Vault:
    def __init__(self, p, n, title, x, y, door):
        self.p, self.n, self.title, self.x, self.y, self.door = p, n, title, x, y, door
        self.needs = []

    # -- names --------------------------------------------------------------------------
    def tok(self, stage):
        return ',v%02d_%s,' % (self.n, stage)

    def lab(self, what):
        return 'Vault %02d %s' % (self.n, what)

    def room(self, k):
        return 300 + self.n * 4 + k

    def at(self, a, r):
        return self.x + math.cos(a) * r, self.y + math.sin(a) * r

    def ground(self, x, y):
        return max(self.p.g.at(x, y), 0.0)

    # -- pieces --------------------------------------------------------------------------
    def tag(self, title, place):
        category, title, text = entry(title)
        return self.p.scan(category, title, text, place, True)

    def stele(self, r=None):
        """The vault's own stele, outside its entrance on the door side: the Scan Visor's part of the puzzle."""
        x, y = self.at(self.door, r if r is not None else self.outer + 900)
        g = self.ground(x, y)
        self.p.mesh(self.lab('Stele'), 'SM_CA_Monolith', (x, y, g - 30), (0, 0, math.degrees(self.door)), (.1, .1, .09), 'Vaults')
        # Half a metre over the stele's tip (the mesh is 22.4 m tall: g - 30 + 2240 * .09 = g + 172). At g + 160 the
        # tag was inside it, where the visor's line of sight never reaches (lantern review, 2026-11-08).
        self.tag(self.title, (x, y, g + 225))
        self.p.light(self.lab('Stele Glow'), (x, y, g + 320), (.6, .8, 1), 1200, 600)

    def ring(self, r, n, gap_angle, floor=None, tall=.75, name='Ring', sealed=False):
        """HumanWall segments on a circle of radius r around the vault, one segment left open at gap_angle.
        floor None puts each segment 1.5 m into the ground under it; a number sits them on a mesa top.
        Returns the gap (x, y, z, yaw) for its gate; the gate's width (local Y) runs along the ring."""
        step = 2 * math.pi / n
        k_gap = -1 if sealed else int(((gap_angle % (2 * math.pi)) / step)) % n
        mid, chord = r * math.cos(step / 2), 2 * r * math.sin(step / 2)
        gap = None
        for k in range(n):
            a = (k + .5) * step
            x, y = self.at(a, mid)
            z = (self.ground(x, y) - 150) if floor is None else floor - 60
            if k == k_gap:
                gap = (x, y, z + (150 if floor is None else 60), math.degrees(a))
                continue
            self.p.mesh(self.lab('%s %d' % (name, k)), 'SM_CA_HumanWall', (x, y, z), (0, 0, math.degrees(a) + 90), ((chord + 160) / 2400, 1.3, tall), 'Vaults')
        self.outer = max(getattr(self, 'outer', 0), r)
        return gap

    def gate(self, kind, gap, give=''):
        """A lock in a wall gap: thorns (Settle) or an ability gate. Each kind carries its scan tag."""
        x, y, z, yaw = gap
        if kind == 'thorn':
            gate = self.p.spawn('BP_SettleBarrier', self.lab('Thorn Gate'), (x, y, z - 40), None, 'Vaults', Give=give)
            gate.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
        else:
            gate = self.socket(kind, self.lab('%s Gate' % TITLE[kind]), (x, y, z), yaw, give, 900.0, True)
        out = math.radians(yaw)
        self.tag(TITLE[kind], (x + math.cos(out) * 260, y + math.sin(out) * 260, z + 420))
        return gate

    def socket(self, kind, label, place, yaw, give='', radius=900.0, solid=False):
        actor = self.p.spawn('BP_AbilitySocket', label, place, None, 'Vaults', Ability=ABILITY[kind], Give=give, Radius=radius,
                             Hold=HOLD.get(kind, 0.0) if solid else 0.0, Solid=solid, Message=USED[kind])
        actor.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
        part = self.p.reskin(actor, MESH[kind])
        if part:
            part.set_collision_profile_name('BlockAll' if solid else 'NoCollision')
        self.p.light(label + ' Glow', (place[0], place[1], place[2] + 380), GLOW[kind], 1600, 900)
        return actor

    def node(self, kind, x, y, z, give):
        """A Resonance node, Reweave anchor or Trace echo: using that ability beside it gives `give`."""
        actor = self.socket(kind, self.lab(TITLE[kind]), (x, y, z), math.degrees(self.door), give, 700.0, False)
        # Half a metre over the socket's mesh. At a fixed 3.3 m a Reweave anchor's tag hung among the anchor's floating
        # fragments, 1.6 m under its top, where the visor's line of sight may not reach (2026-11-08).
        self.tag(TITLE[kind], (x, y, z + self.p.top(MESH[kind]) + 50))
        return actor

    def mesa(self, x, y, top, wx, wy, yaw=0.0, name='Mesa'):
        """A sheer-sided First One block whose top is the vault's floor. Returns the floor height."""
        ca, sa = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        low = min(self.ground(x + ca * u - sa * v, y + sa * u + ca * v) for u in (-wx / 2, 0, wx / 2) for v in (-wy / 2, 0, wy / 2))
        sz = (top - low + 250) / 550
        self.p.mesh(self.lab(name), 'SM_CA_Platform', (x, y, top), (0, 0, yaw), (wx / 600, wy / 520, sz), 'Vaults')
        return top + 8 * sz

    def stair(self, edge, heading, floor, need, name='Step'):
        """A stair that rises (BP_Rise) once `need` is held: built down from the mesa edge at `edge` along
        `heading` (radians, pointing away from the mesa), 105 cm and 4.5 m a step, until it meets the ground."""
        ex, ey = edge
        top, k, steps = floor - 105, 0, []
        while k < 24:
            d = 330 + 450 * k
            x, y = ex + math.cos(heading) * d, ey + math.sin(heading) * d
            g = self.ground(x, y)
            if top < g + 20:
                break
            steps.append((x, y, top, g))
            if top - g <= 130:
                break
            top -= 105
            k += 1
        for i, (x, y, z, g) in enumerate(steps):
            lift = z - g + 450
            self.p.rise(self.lab('%s %d' % (name, i)), 'SM_CA_Platform', (x, y, z), need, lift, (0, 0, math.degrees(heading)), (.6, .6, .35), max(150.0, lift / 2.5))
        foot = steps[-1] if steps else (ex, ey, floor, self.ground(ex, ey))
        return foot

    def bridge(self, a, b, z, need, name='Bridge'):
        """A flat bridge of rising slabs between two points at height z, 4.5 m apart."""
        (ax, ay), (bx, by) = a, b
        span = math.hypot(bx - ax, by - ay)
        count = max(1, int(span / 450))
        yaw = math.degrees(math.atan2(by - ay, bx - ax))
        for i in range(count):
            t = (i + .5) / count
            x, y = ax + (bx - ax) * t, ay + (by - ay) * t
            lift = z - self.ground(x, y) + 450
            self.p.rise(self.lab('%s %d' % (name, i)), 'SM_CA_Platform', (x, y, z), need, lift, (0, 0, yaw), (.6, .6, .35), max(150.0, lift / 2.5))

    def locks(self, k, spots, health=6, high=False, give=None):
        """Crystal locks (static, harmless BP_TrainingDrone targets) in their own room; breaking them all gives
        the stage token. Low ones are for the blade; high ones on pillars only the sidearm reaches."""
        room = self.room(k)
        give = give or self.tok('locks%d' % k)
        for i, (x, y, z) in enumerate(spots):
            drone = self.p.spawn('BP_TrainingDrone', 'Enemy L1 %s' % self.lab('Lock %d %d' % (k, i)), (x, y, z), (.35, .35, .35), 'Vaults',
                                 RoomId=room, Boss=False, Health=health)
            drone.set_editor_property('Static', True)
            self.p.reskin(drone, 'SM_CT_Crystal1' if high else 'SM_CT_Crystal0')
            tag = self.tag(TITLE['prism' if high else 'lock'], (x, y, z + 60))
            tag.attach_to_actor(drone, 'None', unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
            self.p.light(self.lab('Lock Glow %d %d' % (k, i)), (x, y, z + 200), (1, .5, .4) if not high else (.6, .9, 1), 900, 500)
        x, y = spots[0][:2]
        self.p.encounter(self.lab('Locks %d' % k), x, y, room, give, 'The crystal locks shatter. Somewhere in the vault, something gives way.', '')
        self.needs.append(give)
        return give

    def pillar_lock(self, k, spots, height, base=None):
        """Prisms on pillars `height` cm tall: the sidearm's targets."""
        tops = []
        for i, (x, y) in enumerate(spots):
            g = self.ground(x, y) if base is None else base
            self.p.mesh(self.lab('Prism Pillar %d %d' % (k, i)), 'SM_CA_HumanPillar', (x, y, g - 40), (0, 0, 15 * i), (1.0, 1.0, (height + 40) / 920), 'Vaults')
            tops.append((x, y, g + height + 120))
        return self.locks(k, tops, 1, True)

    def guards(self, k, level, spots, floor=None, court=None):
        """Enemies in a room + BP_Encounter. Being a fight's, they are gold (Place.enemy). level is one level or one
        per spot. court (x, y, radius) is the walled court they guard: the encounter stands at its middle on its
        floor and shows 'N left' as the objective only while she is inside it (center_overrides FightLine, 3D
        distance), never to someone walking past a vault still sealed by a later ability."""
        room = self.room(k)
        give = self.tok('guards%d' % k)
        levels = level if isinstance(level, (tuple, list)) else (level,) * len(spots)
        for i, ((x, y), each) in enumerate(zip(spots, levels)):
            enemy = self.p.enemy(each, self.lab('Guard %d %d' % (k, i)), x, y, room)
            if floor is not None:
                hover = enemy.get_actor_location().z - max(self.p.g.at(x, y), 0)
                enemy.set_actor_location(unreal.Vector(x, y, floor + hover), False, False)
        cx, cy, radius = court or (spots[0][0], spots[0][1], 2500.0)
        fight = self.p.encounter(self.lab('Guards %d' % k), cx, cy, room, give, 'The vault\'s guardians fall still.', '',
                                 'Defeat the vault\'s golden guardians', radius)
        fight.set_actor_location(unreal.Vector(cx, cy, (self.ground(cx, cy) if floor is None else floor) + 100), False, False)
        self.needs.append(give)
        return give

    def wounds(self, spots, size=900, period=0.0, floor=None):
        """Divinity wounds: Settle closes each for good; with a period they pulse in turn, so they can be timed."""
        for i, (x, y) in enumerate(spots):
            z = (self.ground(x, y) if floor is None else floor) + 3
            self.p.spawn('BP_Hazard', 'Wound %s' % self.lab('%d' % i), (x, y, z), (size / 100, size / 100, 1), 'Vaults',
                         Deep=False, Off=self.tok('w%d' % i), Period=period, Offset=i * 2.1 if period else 0.0)

    def chain(self, spots, tallest_first=True):
        """Four stones woken in order of size (the stele gives the order); they do not stand in that order."""
        sizes = (.12, .17, .22, .27)
        order = sorted(range(len(spots)), key=lambda i: -sizes[i] if tallest_first else sizes[i])
        give = self.tok('stones')
        for rank, i in enumerate(order):
            x, y = spots[(i * 3 + 1) % len(spots)]
            last = rank == len(order) - 1
            stone = self.p.switch(self.lab('Stone %d' % rank), (x, y, self.ground(x, y) - 40), 0, 'SM_CA_Monolith', True,
                                  Give=give if last else self.tok('stone%d' % (rank + 1)), Need='' if rank == 0 else self.tok('stone%d' % rank),
                                  Denied='The stone stays cold. Another must wake before it. The stele knows the order.',
                                  Done='The last stone wakes, and the court answers.' if last else 'The stone wakes with a low note.')
            stone.set_actor_scale3d(unreal.Vector(sizes[i], sizes[i], sizes[i]))
            self.p.light(self.lab('Stone Glow %d' % rank), (x, y, self.ground(x, y) + 2340 * sizes[i] + 100), (.6, .8, 1), 1200, 700)
        self.needs.append(give)
        return give

    def reward(self, kind, index, x=None, y=None, floor=None):
        """The augmentation on a dais that rises when every stage is done. Shown from the start, out of reach."""
        x = self.x if x is None else x
        y = self.y if y is None else y
        floor = self.ground(x, y) if floor is None else floor
        title, mesh, colour, done = AUG[kind]
        opened = self.tok('open')
        needs = list(self.needs)
        while len(needs) > 4:
            joined = self.tok('join%d' % len(needs))
            self.p.require(self.lab('Join %d' % len(needs)), (x, y, floor + 600), needs[:4], joined, '')
            needs = [joined] + needs[4:]
        self.p.require(self.lab('Open'), (x, y, floor + 600), needs, opened, 'The vault opens. Its %s rises into the light.' % title)
        self.p.rise(self.lab('Dais'), 'SM_CA_Platform', (x, y, floor + 60), opened, 260, (0, 0, 0), (.6, .6, .5), 90)
        relic = self.p.relic(self.lab(title), (x, y, floor + 190), ',aug_%s%d,' % (kind, index), done, opened, 0.0, kind == 'hp', mesh, 1.0)
        relic.set_editor_property('Tease', True)
        relic.set_editor_property('Locked', LOCKED)
        self.tag(title, (x, y, floor + 260))
        self.p.light(self.lab('Prize Glow'), (x, y, floor + 520), colour, 3000, 1400)
        return relic


# ---------------------------------------------------------------- the fifteen vaults
# Courts are the rings between walls; gates alternate sides so every court must be crossed.

def patient_heart(v):  # Health 1: blade, Settle, Light Step, Resonance Link, Dissonance
    d = v.door
    v.gate('thorn', v.ring(2800, 15, d))
    v.wounds([v.at(d + 1.2, 2300), v.at(d - 1.2, 2300)], 800, 3.0)
    v.locks(0, [(*v.at(d + a, 2300), v.ground(*v.at(d + a, 2300)) + 90) for a in (2.0, math.pi, -2.0)], 6)
    v.gate('light', v.ring(1800, 11, d + math.pi))
    nx, ny = v.at(d + math.pi / 2, 1350)
    v.node('node', nx, ny, v.ground(nx, ny), v.tok('node'))
    v.needs.append(v.tok('node'))
    v.gate('field', v.ring(900, 6, d))
    v.reward('hp', 1)
    v.stele()


def high_ledger(v):  # Health 2: Trace Reading, Sit With, sidearm, Settle
    d = v.door
    floor = v.mesa(v.x, v.y, v.ground(v.x, v.y) + 1100, 2800, 2800, math.degrees(d))
    edge = v.at(d, 1400)
    fx, fy, _, fg = v.stair(edge, d, floor, v.tok('stair'))
    ex, ey = fx + math.cos(d + 1.57) * 500, fy + math.sin(d + 1.57) * 500
    v.node('echo', ex, ey, v.ground(ex, ey), v.tok('stair'))
    v.gate('grief', v.ring(1050, 8, d, floor, .5))
    v.pillar_lock(0, [v.at(d + 2.2, 650), v.at(d - 2.2, 650)], 600, floor)
    v.wounds([v.at(d + math.pi, 0)], 700, 0.0, floor)
    v.reward('hp', 2, floor=floor)
    v.stele(1400 + 450 * 12)


def unwoven_span(v):  # Health 3: Reweave, Settle, combat, Light Step
    d = v.door
    floor = v.mesa(v.x, v.y, v.ground(v.x, v.y) + 900, 3200, 3200, math.degrees(d))
    fx, fy, _, _ = v.stair(v.at(d, 1600), d, floor, v.tok('ramp'), 'Ramp')
    ax, ay = fx + math.cos(d - 1.57) * 500, fy + math.sin(d - 1.57) * 500
    v.node('anchor', ax, ay, v.ground(ax, ay), v.tok('ramp'))
    v.gate('thorn', v.ring(1400, 10, d, floor, .55))
    v.guards(0, 3, [v.at(d + a, 1000) for a in (1.6, math.pi, -1.6)], floor, (v.x, v.y, 1400))
    v.gate('light', v.ring(650, 6, d + math.pi, floor, .5))
    v.reward('hp', 3, floor=floor)
    v.stele(1600 + 450 * 10)


def long_silence(v):  # Health 4: Sit With, Scan order, Settle, blade, Dissonance
    d = v.door
    v.gate('grief', v.ring(2900, 16, d))
    v.chain([v.at(d + a, 2400) for a in (1.0, 2.0, -1.0, -2.0)], True)
    v.gate('thorn', v.ring(1900, 12, d + math.pi))
    v.locks(0, [(*v.at(d + a, 1400), v.ground(*v.at(d + a, 1400)) + 90) for a in (1.2, -1.2)], 6)
    v.gate('field', v.ring(900, 6, d))
    v.reward('hp', 4)
    v.stele()


def court_of_edges(v):  # Katana 1: Light Step, blade, timing or Settle, Settle
    d = v.door
    v.gate('light', v.ring(2600, 14, d))
    spots = [v.at(d + .9 + k * (2 * math.pi - 1.8) / 5, 1850) for k in range(6)]
    v.locks(0, [(x, y, v.ground(x, y) + 90) for x, y in spots], 8)
    v.wounds([v.at(d + a, 1850) for a in (1.6, math.pi, -1.6)], 900, 3.0)
    v.gate('thorn', v.ring(1100, 7, d + math.pi))
    v.reward('katana', 1)
    v.stele()


def resonant_blades(v):  # Katana 2: Resonance Link x3, blade, Settle
    d = v.door
    tops, spots, places = [], [], []
    for k in range(3):
        a = d + math.pi + (k - 1) * 2.1
        places.append((v.at(a, 1700) if k != 1 else v.at(d + math.pi, 2400), a))
    # One floor for all three, so every bridge is level: 5.5 m above the highest ground under them.
    top = max(v.ground(x, y) for (x, y), a in places) + 550
    for k, ((x, y), a) in enumerate(places):
        tops.append((x, y, v.mesa(x, y, top, 1000, 1000, math.degrees(a), 'Stone %d' % k)))
    # The first stone's stair rises from a node at its foot; each stone's node raises the bridge to the next.
    x0, y0, f0 = tops[0]
    heading = math.atan2(y0 - v.y, x0 - v.x)
    fx, fy, _, _ = v.stair((x0 + math.cos(heading) * 500, y0 + math.sin(heading) * 500), heading, f0, v.tok('bridge0'), 'Stair')
    v.node('node', fx + math.cos(heading + 1.57) * 450, fy + math.sin(heading + 1.57) * 450, v.ground(fx, fy), v.tok('bridge0'))
    for k in range(2):
        (ax, ay, fa), (bx, by, fb) = tops[k], tops[k + 1]
        u = math.atan2(by - ay, bx - ax)
        v.node('node', ax - math.cos(u) * 250, ay - math.sin(u) * 250, fa, v.tok('bridge%d' % (k + 1)))
        v.bridge((ax + math.cos(u) * 560, ay + math.sin(u) * 560), (bx - math.cos(u) * 560, by - math.sin(u) * 560), max(fa, fb) - 5, v.tok('bridge%d' % (k + 1)),
                 'Span%d' % (k + 1))
    for k, (x, y, floor) in enumerate(tops):
        spots.append((x + 200, y, floor + 90))
    v.locks(0, spots, 6)
    for k, (x, y, floor) in enumerate(tops[:2]):
        v.p.spawn('BP_Hazard', 'Wound %s' % v.lab('Stone %d' % k), (x - 200, y, floor + 3), (5, 5, 1), 'Vaults', Deep=False, Off=v.tok('w%d' % k), Period=0.0, Offset=0.0)
    x, y, floor = tops[2]
    v.reward('katana', 2, x - 150, y - 150, floor)
    v.stele(2600)


def rewoven_arena(v):  # Katana 3: Reweave, Settle, combat, blade
    d = v.door
    floor = v.mesa(v.x, v.y, v.ground(v.x, v.y) + 700, 3800, 3800, math.degrees(d))
    fx, fy, _, _ = v.stair(v.at(d, 1900), d, floor, v.tok('ramp'), 'Ramp')
    v.node('anchor', fx + math.cos(d + 1.57) * 500, fy + math.sin(d + 1.57) * 500, v.ground(fx, fy), v.tok('ramp'))
    v.gate('thorn', v.ring(1650, 11, d, floor, .55))
    # One fight for all three guardians since 2026-11-08: two encounters in one arena would take turns showing their
    # counts, and each would count only its own.
    v.guards(0, (3, 3, 4), [v.at(d + 1.8, 1100), v.at(d - 1.8, 1100), v.at(d + math.pi, 1000)], floor, (v.x, v.y, 1650))
    v.locks(2, [(*v.at(d + a, 450), floor + 90) for a in (1.0, -1.0)], 8)
    v.reward('katana', 3, floor=floor)
    v.stele(1900 + 450 * 8)


def prism_gallery(v):  # Pistol 1: Settle, sidearm, Light Step
    d = v.door
    v.gate('thorn', v.ring(2600, 14, d))
    v.pillar_lock(0, [v.at(d + a, 1800) for a in (1.2, 2.4, -2.4, -1.2)], 800)
    v.gate('light', v.ring(1000, 7, d + math.pi))
    v.reward('pistol', 1)
    v.stele()


def far_lights(v):  # Pistol 2: Reweave, Settle, long sidearm shots, Dissonance
    d = v.door
    floor = v.mesa(v.x, v.y, v.ground(v.x, v.y) + 800, 2600, 2600, math.degrees(d))
    fx, fy, _, _ = v.stair(v.at(d, 1300), d, floor, v.tok('ramp'), 'Ramp')
    v.node('anchor', fx + math.cos(d + 1.57) * 500, fy + math.sin(d + 1.57) * 500, v.ground(fx, fy), v.tok('ramp'))
    v.wounds([v.at(d + 1.3, 800), v.at(d - 1.3, 800)], 600, 0.0, floor)
    # Three prisms far out on the plain, each in a closed court of walls: only the observatory sees over them.
    spots = []
    for k, a in enumerate((d + math.pi, d + math.pi - 1.1, d + math.pi + 1.1)):
        px, py = v.at(a, 2900)
        Vault(v.p, v.n, v.title, px, py, a).ring(650, 7, 0, None, .75, 'Court %d' % k, True)
        g = v.ground(px, py)
        v.p.mesh(v.lab('Prism Pillar %d' % k), 'SM_CA_HumanPillar', (px, py, g - 40), (0, 0, 0), (1.0, 1.0, 440 / 920), 'Vaults')
        spots.append((px, py, g + 400 + 120))
    v.locks(0, spots, 1, True)
    v.gate('field', v.ring(650, 6, d, floor, .5))
    v.reward('pistol', 2, floor=floor)
    v.stele(1300 + 450 * 9)


def sentinel_hold(v):  # Defense 2: Sit With, combat (Hollow Sentinel), Settle
    d = v.door
    v.gate('grief', v.ring(3000, 16, d))
    v.guards(0, 5, [v.at(d + math.pi, 2000)], None, (v.x, v.y, 2900))
    v.gate('thorn', v.ring(1000, 7, d + math.pi))
    v.reward('defense', 2)
    v.stele()


def burning_stair(v):  # Defense 3: timing or Settle, Reweave, combat
    d = v.door
    floor = v.mesa(v.x, v.y, v.ground(v.x, v.y) + 1000, 2200, 2200, math.degrees(d))
    # A visible stone stair up the door side; its landings burn in pulses.
    edge = v.at(d, 1100)
    top, k = floor - 105, 0
    while k < 20:
        dd = 330 + 450 * k
        x, y = edge[0] + math.cos(d) * dd, edge[1] + math.sin(d) * dd
        g = v.ground(x, y)
        if top < g + 20:
            break
        v.p.mesh(v.lab('Burning Step %d' % k), 'SM_CA_Platform', (x, y, top), (0, 0, math.degrees(d)), (.6, .6, .35), 'Vaults')
        if k % 3 == 1:
            v.p.spawn('BP_Hazard', 'Wound %s' % v.lab('Step %d' % k), (x, y, top + 3), (5.6, 5.6, 1), 'Vaults', Deep=False,
                      Off=v.tok('w%d' % k), Period=2.6, Offset=k * 1.3)
        if top - g <= 130:
            break
        top -= 105
        k += 1
    # The far stone, across a broken bridge.
    far = v.at(d + math.pi, 2300)
    far_floor = v.mesa(far[0], far[1], floor - 15, 1200, 1200, math.degrees(d), 'Far Stone')
    v.node('anchor', *v.at(d + math.pi, 700), floor, v.tok('bridge'))
    v.bridge(v.at(d + math.pi, 1200), v.at(d + math.pi, 1650), floor - 5, v.tok('bridge'))
    v.guards(0, 3, [(far[0] + 250, far[1] + 250), (far[0] - 250, far[1] - 250)], far_floor, (far[0], far[1], 900))
    v.reward('defense', 3, far[0], far[1], far_floor)
    v.stele(1100 + 450 * 11)


def pulse_garden(v):  # Agility 2: Settle, timing, sidearm, Light Step, Resonance Link
    d = v.door
    v.gate('thorn', v.ring(2600, 14, d))
    v.wounds([v.at(d + .4 + k * (2 * math.pi - .8) / 7, 1850) for k in range(8)], 1000, 2.4)
    px, py = v.at(d + math.pi + .45, 1350)
    v.pillar_lock(0, [(px, py)], 700)
    v.gate('light', v.ring(1100, 7, d + math.pi))
    nx, ny = v.at(d + math.pi / 2, 600)
    v.node('node', nx, ny, v.ground(nx, ny), v.tok('node'))
    v.needs.append(v.tok('node'))
    v.reward('agility', 2)
    v.stele()


def drift_spire(v):  # Agility 3: timing jumps, Trace Reading, Settle, blade
    d = v.door
    base = v.ground(v.x, v.y)
    crown = base + 14 * 105 + 100
    v.p.mesh(v.lab('Spire'), 'SM_CA_HumanPillar', (v.x, v.y, base - 40), (0, 0, 0), (2.2, 2.2, (crown - base - 400) / 920), 'Vaults')
    v.p.mesh(v.lab('Crown'), 'SM_CA_Platform', (v.x, v.y, crown), (0, 0, math.degrees(d)), (2.4, 2.6, .8), 'Vaults')
    floor = crown + 8 * .8
    for k in range(14):
        a = d + k * .5
        x, y = v.at(a, 1150 + 20 * (k % 2))
        z = base + 105 * (k + 1)
        if k == 8:
            v.p.mesh(v.lab('Landing'), 'SM_CA_Platform', (x, y, z), (0, 0, math.degrees(a)), (.9, .9, .3), 'Vaults')
        elif k < 8:
            plat = v.p.spawn('BP_Platform', v.lab('Drift %d' % k), (x, y, z), None, 'Vaults', AmpX=0.0, AmpY=0.0, AmpZ=45.0, Period=4.0 + .5 * (k % 4), Need='')
            v.p.reskin(plat, 'SM_CA_Platform')
            plat.set_actor_rotation(unreal.Rotator(0, 0, math.degrees(a)), False)
            plat.set_actor_scale3d(unreal.Vector(.6, .6, .3))
        else:
            lift = z - v.ground(x, y) + 450
            v.p.rise(v.lab('Trace Step %d' % k), 'SM_CA_Platform', (x, y, z), v.tok('trace'), lift, (0, 0, math.degrees(a)), (.6, .6, .3), max(150.0, lift / 2.5))
    ex, ey = v.at(d + 8 * .5, 1150)
    v.node('echo', ex + math.cos(d + 4) * 150, ey + math.sin(d + 4) * 150, base + 105 * 9 + 3, v.tok('trace'))
    v.wounds([(v.x + 330, v.y), (v.x - 330, v.y)], 500, 0.0, floor)
    v.locks(0, [(v.x, v.y + 420, floor + 90)], 8)
    v.reward('agility', 3, v.x, v.y - 330, floor)
    v.stele(2200)


def corridor(v, length, walls='wall'):
    """An axis-aligned walled run from the entrance (u = -length/2) to a sealed end, 10 m wide inside.
    Returns spot(u, v) -> (x, y) and the floor height function."""
    ca, sa = math.cos(v.door), math.sin(v.door)
    spot = lambda u, w: (v.x + ca * u - sa * w, v.y + sa * u + ca * w)
    half = length / 2
    count = int(math.ceil(length / (2300 if walls == 'wall' else 900)))
    for k in range(count):
        u = -half + (k + .5) * length / count
        for side in (-1, 1):
            x, y = spot(u, side * 590)
            if walls == 'wall':
                v.p.mesh(v.lab('Run Wall %d %d' % (k, side)), 'SM_CA_HumanWall', (x, y, v.ground(x, y) - 150), (0, 0, math.degrees(v.door)),
                         ((length / count + 160) / 2400, 1.3, .75), 'Vaults')
            else:
                x, y = spot(u, side * 800)
                v.p.mesh(v.lab('Run Rock %d %d' % (k, side)), 'SM_CT_Rock2', (x, y, v.ground(x, y) - 120), (0, 0, math.degrees(v.door) + side * 3),
                         (.6, .55, .6), 'Vaults')
    x, y = spot(half + 120, 0)
    v.p.mesh(v.lab('Run End'), 'SM_CA_HumanWall', (x, y, v.ground(x, y) - 150), (0, 0, math.degrees(v.door) + 90), (.62, 1.3, .75), 'Vaults')
    return spot


def lattice_run(v):  # Agility 1: Settle, Light Step x3 (timed), timing, sidearm
    spot = corridor(v, 9000)
    yaw = math.degrees(v.door)
    # The gates' tags stand 3-4 m in front of them, toward the entrance. On the gates' own axis they were inside the
    # solid gates (lantern review, 2026-11-08), where the visor's line of sight never reaches.
    x, y = spot(-4300, 0)
    gate = v.p.spawn('BP_SettleBarrier', v.lab('Thorn Gate'), (x, y, v.ground(x, y) - 40))
    gate.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
    x, y = spot(-4700, 0)
    v.tag('Thorn Barrier', (x, y, v.ground(x, y) + 250))
    for k, u in enumerate((-2600, -400, 1800)):
        x, y = spot(u, 0)
        v.socket('light', v.lab('Lattice %d' % k), (x, y, v.ground(x, y)), yaw, '', 900.0, True)
        x, y = spot(u - 300, 0)
        v.tag('Light Lattice', (x, y, v.ground(x, y) + 250))
    v.wounds([spot(-1500, 0), spot(700, 0), spot(2900, 0)], 1100, 2.2)
    px, py = spot(4250, 0)
    v.pillar_lock(0, [(px, py)], 750)
    rx, ry = spot(3700, 0)
    v.reward('agility', 1, rx, ry)
    v.stele(-5100)


def furnace_walk(v):  # Defense 1: Settle x5 (or Mend), combat, Dissonance
    spot = corridor(v, 7600, 'rock')
    yaw = math.degrees(v.door)
    v.wounds([spot(u, 0) for u in (-2700, -1600, -500, 600, 1700)], 1100, 0.0)
    # The run is 10 m wide inside its rocks: 12 m round the guards' end covers it and not the far side of the rocks.
    v.guards(0, 4, [spot(2600, 250), spot(2600, -250)], None, (*spot(2600, 0), 1200))
    x, y = spot(3050, 0)
    v.socket('field', v.lab('Field Gate'), (x, y, v.ground(x, y)), yaw + 0, '', 900.0, True)
    x, y = spot(2750, 0)
    v.tag('Dissonance Field', (x, y, v.ground(x, y) + 250))  # 3 m before the gate
    rx, ry = spot(3500, 0)
    v.reward('defense', 1, rx, ry)
    v.stele(-4500)


# Title, builder, footprint kind: ring vaults want the flattest ground, corridors a flat axis-aligned strip,
# mesas take what is left.
VAULTS = (('Vault of the Patient Heart', patient_heart, 'ring'), ('Vault of the High Ledger', high_ledger, 'mesa'),
          ('Vault of the Unwoven Span', unwoven_span, 'mesa'), ('Vault of the Long Silence', long_silence, 'ring'),
          ('Court of Edges', court_of_edges, 'ring'), ('The Resonant Blades', resonant_blades, 'mesa'),
          ('The Rewoven Arena', rewoven_arena, 'mesa'), ('The Prism Gallery', prism_gallery, 'ring'),
          ('The Far Lights', far_lights, 'mesa'), ('The Furnace Walk', furnace_walk, 'run'),
          ('The Sentinel Hold', sentinel_hold, 'ring'), ('The Burning Stair', burning_stair, 'mesa'),
          ('The Lattice Run', lattice_run, 'run'), ('The Pulse Garden', pulse_garden, 'ring'),
          ('The Drift Spire', drift_spire, 'mesa'))


def nearest_road(road_lines, x, y):
    best, point = 1e18, (x, y)
    for line in road_lines:
        for (ax, ay), (bx, by) in zip(line, line[1:]):
            ax, ay, bx, by = ax * 100, ay * 100, bx * 100, by * 100
            dx, dy = bx - ax, by - ay
            t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / max(dx * dx + dy * dy, 1.0)))
            px, py = ax + dx * t, ay + dy * t
            d = math.hypot(x - px, y - py)
            if d < best:
                best, point = d, (px, py)
    return best, point


def choose_sites(p, road_lines, taken):
    """Sites for every vault: ring vaults on the flattest ground (relief over 32 m), runs on flat axis-aligned
    strips, mesas anywhere dry; all off the roads, clear of hubs, puzzles, Still Points and each other, spread out.
    Returns [(x, y, door)], the door facing the nearest road."""
    def relief(x, y, r):
        h = [p.g.at(x + math.cos(a) * rr, y + math.sin(a) * rr) for rr in (r * .5, r) for a in [k / 12 * 2 * math.pi for k in range(12)]] + [p.g.at(x, y)]
        return max(h) - min(h), min(h)

    cands = []
    for gx in range(-75000, 75001, 2500):
        for gy in range(-75000, 75001, 2500):
            if any(math.hypot(gx - tx, gy - ty) < tr for tx, ty, tr in taken):
                continue
            rel, low = relief(gx, gy, 3300)
            if low < 80 or rel > 700:
                continue
            gap, _ = nearest_road(road_lines, gx, gy)
            if gap < 4000:
                continue
            cands.append((gx, gy, rel))
    picks = [None] * len(VAULTS)
    placed = []

    def far_enough(x, y):
        return all(math.hypot(x - qx, y - qy) >= 11000 for qx, qy in placed)

    def spread(c):
        return min([math.hypot(c[0] - qx, c[1] - qy) for qx, qy in placed] + [1e9])

    for want in ('ring', 'run', 'mesa'):
        for i, (title, build, kind) in enumerate(VAULTS):
            if kind != want:
                continue
            if kind == 'run':
                pool = []
                for c in cands:
                    if not far_enough(c[0], c[1]):
                        continue
                    for yaw in (0, 90, 180, 270):
                        ca, sa = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
                        h = [p.g.at(c[0] + ca * u - sa * w, c[1] + sa * u + ca * w) for u in range(-4800, 4801, 800) for w in (-900, 0, 900)]
                        if min(h) >= 80 and max(h) - min(h) < 220:
                            pool.append((max(h) - min(h), c, math.radians(yaw)))
                if not pool:
                    continue
                pool.sort(key=lambda e: e[0] - spread(e[1]) * .004)
                _, c, door = pool[0]
                picks[i] = (c[0], c[1], door)
            else:
                pool = []
                for limit in ((420, 600) if kind == 'ring' else (700,)):
                    pool = [c for c in cands if c[2] <= limit and far_enough(c[0], c[1])]
                    if pool:
                        break
                if not pool:
                    continue
                c = max(pool, key=lambda c: spread(c) - c[2] * 20)
                _, (rx, ry) = nearest_road(road_lines, c[0], c[1])
                picks[i] = (c[0], c[1], math.atan2(ry - c[1], rx - c[0]))
            placed.append(picks[i][:2])
    return picks


def build(p, road_lines, taken):
    """Builds every vault; returns [(title, x, y)] for the scenario's site list."""
    sites = choose_sites(p, road_lines, taken)
    out = []
    for n, ((title, builder, kind), site) in enumerate(zip(VAULTS, sites), 1):
        if site is None:
            unreal.log_warning('No site for %s' % title)
            continue
        x, y, door = site
        builder(Vault(p, n, title, x, y, door))
        out.append((title, round(x), round(y)))
    return out
