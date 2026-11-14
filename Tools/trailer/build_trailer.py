"""Cuts the Physis trailer from the Movie Render Queue frames in Saved/Trailer and the game's own audio.
Timeline: the awakening cold open (eye, gasp), Meridian Station (opening battle, interiors), the rise and reveal with
Physis's awakening line, the Center montage, the title card. Prints the timeline and writes the ffmpeg command."""
import json, subprocess, sys, os
P = '/home/precosmos/PhysisProject'
T = P + '/Saved/Trailer'
A = P + '/Art/Audio'
FPS = 30.0
# (segment, source dir, first frame, frames, transition into the NEXT clip: (kind, seconds))
CLIPS = [
    ('A', 'awakening', 0, 270, ('fadeblack', 0.6)),     # black, heartbeat, the eye opens, the gasp, lying still
    ('B', 'opening', 360, 105, ('fade', 0.4)),          # nebula, the fleets
    ('B', 'opening', 540, 135, ('fade', 0.4)),          # the battle
    ('B', 'opening', 825, 105, ('fade', 0.4)),          # Meridian Station
    ('B', 'opening', 1063, 75, ('fade', 0.4)),          # the hangar
    ('B', 'station', 10, 90, ('fade', 0.4)),            # the hall
    ('B', 'station', 130, 90, ('fade', 0.4)),           # the Spine
    ('B', 'station', 255, 105, ('fadeblack', 0.6)),     # the boss hall
    ('C', 'awakening', 300, 180, ('fade', 0.4)),        # she rises
    ('C', 'awakening', 615, 165, ('fade', 0.5)),        # the reveal (Divinity speaks)
    ('D', 'center', 0, 120, ('fade', 0.4)),             # aerial over the rays
    ('D', 'center', 165, 120, ('fade', 0.1)),           # the Concourse Ring
    ('D', 'combat1', 0, 78, ('fade', 0.1)),             # katana combo: Cut, Slice, Whirl, the Shardling bursts
    ('D', 'center', 320, 105, ('fade', 0.1)),           # crystals, jellyfish, aurora
    ('D', 'combat2', 0, 105, ('fade', 0.1)),            # Divine Parry and the Cyclone counter
    ('D', 'center', 465, 90, ('fade', 0.1)),            # Lantern Marsh
    ('D', 'combat3', 0, 90, ('fade', 0.3)),             # the sidearm: three shots, a burst
    ('D', 'center', 615, 90, ('fade', 0.4)),            # Choir Hollow
    ('D', 'center', 765, 90, ('fade', 0.4)),            # Glass Highlands
    ('D', 'center', 900, 150, ('fadeblack', 1.0)),      # the Temple of the First Light
]
TITLE = (P + '/Art/Review/logo_final_title.png', 7.0)
starts, t = [], 0.0
for i, (seg, src, first, n, (kind, d)) in enumerate(CLIPS):
    starts.append(t)
    t += n / FPS - d          # the next clip starts d seconds before this one ends
title_start = t
total = title_start + TITLE[1]
seg_start = {}
for (seg, *_), s in zip(CLIPS, starts):
    seg_start.setdefault(seg, s)
lenB = seg_start['C'] - seg_start['B']
lenC = seg_start['D'] - seg_start['C']
reveal = starts[9]
args = ['ffmpeg', '-y', '-hide_banner', '-loglevel', 'warning']
filters = []
for i, (seg, src, first, n, _) in enumerate(CLIPS):
    args += ['-framerate', '30', '-start_number', str(first), '-i', '%s/%s/%%05d.jpeg' % (T, src)]
    filters.append('[%d:v]trim=end_frame=%d,setpts=PTS-STARTPTS,fps=30,scale=1920:1080:in_range=pc:out_range=tv:in_color_matrix=bt601:out_color_matrix=bt709,setsar=1,format=yuv420p[v%d]' % (i, n, i))
ti = len(CLIPS)
args += ['-loop', '1', '-framerate', '30', '-t', str(TITLE[1]), '-i', TITLE[0]]
filters.append('[%d:v]scale=1728:1080:out_range=tv:out_color_matrix=bt709,format=yuv420p,pad=1920:1080:96:0:black,setsar=1,fps=30,fade=t=out:st=%.2f:d=1.5[v%d]' % (ti, TITLE[1] - 1.6, ti))
prev = 'v0'
for i in range(1, len(CLIPS) + 1):
    kind, d = CLIPS[i - 1][4]
    offset = (starts[i] if i < len(CLIPS) else title_start)
    out = 'x%d' % i
    filters.append('[%s][v%d]xfade=transition=%s:duration=%.2f:offset=%.3f[%s]' % (prev, i, kind, d, offset, out))
    prev = out
video_out = prev
# Audio: the game's own sounds at the cinematic's timings, then the station and Center scores.
audio = [  # file, source start s, length s, trailer time s, volume, fade in s, fade out s
    (A + '/Center/S_Music_Awakening.wav', 0.0, 9.4, 0.0, 0.65, 0.0, 0.9),
    (A + '/Center/S_Awaken_Heart.wav', 0.0, 3.0, 0.3, 0.9, 0.0, 0.0),
    (A + '/Center/S_Awaken_Heart.wav', 0.0, 3.0, 2.6, 0.9, 0.0, 0.0),
    (A + '/Center/S_Awaken_Gasp.wav', 0.0, 7.88, 4.3, 1.0, 0.0, 0.6),
    (A + '/S_Opening.wav', 14.0, lenB + 0.6, seg_start['B'] - 0.3, 0.9, 0.6, 1.0),
    (A + '/Center/S_Music_Awakening.wav', 20.5 - (reveal - seg_start['C']), lenC + 2.5, seg_start['C'] - 0.3, 0.75, 0.6, 2.5),
    (A + '/Voice/Center/S_VO_Awakening.wav', 0.0, 13.0, reveal + 0.5, 1.15, 0.0, 0.3),
    (A + '/Center/S_Music_Center.wav', 45.0, total - seg_start['D'] + 1.5, seg_start['D'] - 1.5, 0.8, 2.5, 3.0),
]
G = A + '/Game/'
SFX = {'combat1': [(G + 'S_SwordSwing1.wav', .33), (G + 'S_SwordHit1.wav', .50), (G + 'S_SwordSwing2.wav', 1.0), (G + 'S_SwordHit2.wav', 1.13),
                   (G + 'S_SwordSwing3.wav', 1.63), (G + 'S_SwordHeavy.wav', 1.83), (G + 'S_DroneExplosion.wav', 1.87)],
       'combat2': [(G + 'S_SwordHeavy.wav', .27), (G + 'S_Laser1.wav', .67), (G + 'S_Parry.wav', 1.6), (G + 'S_Block.wav', 1.6),
                   (G + 'S_SwordSwing3.wav', 1.83), (G + 'S_SwordSwing2.wav', 2.2), (G + 'S_SwordSwing1.wav', 2.67)],
       'combat3': [(G + 'S_Laser2.wav', .43), (G + 'S_LaserHit.wav', .47), (G + 'S_Laser2.wav', 1.03), (G + 'S_LaserHit.wav', 1.07),
                   (G + 'S_Laser2.wav', 1.63), (G + 'S_LaserHit.wav', 1.67), (G + 'S_DroneExplosion.wav', 1.7)]}
for (seg, src, first, n, _), s0 in zip(CLIPS, starts):
    for path, t in SFX.get(src, []):
        audio.append((path, 0.0, 6.0, s0 + t, 0.9, 0.0, 0.05))
mix = []
for k, (path, src_start, length, at, vol, fin, fout) in enumerate(audio):
    idx = ti + 1 + k
    args += ['-i', path]
    chain = '[%d:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=start=%.3f:duration=%.3f,asetpts=PTS-STARTPTS,volume=%.2f' % (idx, src_start, length, vol)
    if fin:
        chain += ',afade=t=in:st=0:d=%.2f' % fin
    if fout:
        chain += ',afade=t=out:st=%.3f:d=%.2f' % (length - fout, fout)
    chain += ',adelay=%d:all=1[a%d]' % (int(at * 1000), k)
    filters.append(chain)
    mix.append('[a%d]' % k)
# a5 (awakening score under the reveal) and a7 (Center score) duck under a6 (the voice).
filters.append('[a5][a7]amix=inputs=2:normalize=0:dropout_transition=0[mus]')
filters.append('[a6]asplit=2[vokey0][vo]')
filters.append('[vokey0]apad[vokey]')  # the key must outlast the scores: a finished key ends the compressor's output
filters.append('[mus][vokey]sidechaincompress=threshold=0.02:ratio=6:attack=40:release=600[musd]')
rest = [m for m in mix if m not in ('[a5]', '[a6]', '[a7]')] + ['[musd]', '[vo]']
filters.append('%samix=inputs=%d:normalize=0:dropout_transition=0:duration=longest,apad,atrim=duration=%.3f,loudnorm=I=-16:TP=-1.5:LRA=11[aout]' % (''.join(rest), len(rest), total))
out_path = T + '/Physis_Trailer.mp4'
args += ['-filter_complex', ';'.join(filters), '-map', '[%s]' % video_out, '-map', '[aout]',
         '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', '-r', '30',
         '-color_range', 'tv', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
         '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart', '-t', '%.3f' % total, out_path]
timeline = {'segments': {k: round(v, 2) for k, v in seg_start.items()}, 'reveal': round(reveal, 2), 'title': round(title_start, 2), 'total': round(total, 2)}
print(json.dumps(timeline))
if '--run' in sys.argv:
    r = subprocess.run(args)
    print('exit', r.returncode)
