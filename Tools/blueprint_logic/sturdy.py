"""BP_TrainingDrone.Sturdy: an enemy the station's clean-up never destroys.

The station (no BP_Awakening in the level) destroys a drone it judges jammed: pressed against another for 1.5 s, sunk
in the floor, or not moved 60 cm in 2.5 s (DroneStuckCheck). Those tests were made for the small machines. The author,
2026-11-18, of the station's one elemental monster: "I just played the whole Battle Station sequence. There was no
Pyre Lion". A Play test showed it alive at the start and destroyed within a second and a half of her entering its
room: a three-metre animal is "sunk" by the machines' measure. Sturdy turns the three tests off for one enemy;
physis_monsters.monster sets it on every elemental monster. The open levels never ran these tests.

  python3 Tools/blueprint_logic/sturdy.py        (the GUI editor running; safe to run again)
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import elements as e  # noqa: E402  (its client and helpers)

NOT = '(not (`self.Sturdy`))'


def main():
    e.client.initialize()   # without a session the editor answers every call with HTTP 400
    e.var(e.D, 'Sturdy', 'bool', True)
    e.edit(e.D, 'DroneStuckCheck', 'self.Sturdy', [
        ('(if (>= (`self.PairFor`) 1.5)', '(if (and (>= (`self.PairFor`) 1.5) %s)' % NOT),
        ('(if (and _returnvalue_2 (or _returnvalue_3 (< (.z _returnvalue) 40.0)))', '(if (and (and _returnvalue_2 %s) (or _returnvalue_3 (< (.z _returnvalue) 40.0)))' % NOT),
        ('(and (not (`self.BlockedSeen`)) (< (`KismetMathLibrary.Vector_Distance` _returnvalue (`self.LastSpot`)) 60.0))',
         '(and (and (not (`self.BlockedSeen`)) %s) (< (`KismetMathLibrary.Vector_Distance` _returnvalue (`self.LastSpot`)) 60.0))' % NOT)])
    e.compile_and_save(e.D)
    print('FAILED', e.FAILED) if e.FAILED else print('done')


if __name__ == '__main__':
    main()
