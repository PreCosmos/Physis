# Physis now lies head north (A_Physis_GetUp, LIE_PLACE: turned 180 about Z and shifted (-0.36, 1.47) m in her own
# frame), so SEQ_Awakening's lying shots (camera keys up to frame 294, the cut before the rise) turn 180 degrees about
# the same point: UE (-68473.5, 18). Applied once: the eye close-up key (frame 0) tells whether it already was.
CX, CY, LAST = -68473.5, 18.0, 294
seq = unreal.load_asset('/Game/Center/Cinema/SEQ_Awakening')
cam = next(b for b in seq.get_bindings() if str(b.get_display_name()) == 'Cine Camera')
sec = next(t for t in cam.get_tracks() if t.get_class().get_name() == 'MovieScene3DTransformTrack').get_sections()[0]
ch = sec.get_all_channels()
x0 = [k for k in ch[0].get_keys() if k.get_time().frame_number.value == 0][0].get_value()
if abs(x0 - (2 * CX - (-68547.5))) < 1.0:
    RESULT = {'already': True, 'x0': x0}
else:
    changed = []
    for idx, fn in ((0, lambda v: 2 * CX - v), (1, lambda v: 2 * CY - v), (5, lambda v: v + 180.0)):
        for k in ch[idx].get_keys():
            f = k.get_time().frame_number.value
            if f <= LAST:
                k.set_value(fn(k.get_value()))
                changed.append(f)
    unreal.EditorAssetLibrary.save_asset('/Game/Center/Cinema/SEQ_Awakening', False)
    keys = []
    for k in ch[0].get_keys():
        f = k.get_time().frame_number.value
        if f <= 300:
            y = [q for q in ch[1].get_keys() if q.get_time().frame_number.value == f][0].get_value()
            yaw = [q for q in ch[5].get_keys() if q.get_time().frame_number.value == f][0].get_value()
            keys.append([f, round(k.get_value(), 1), round(y, 1), round(yaw, 1)])
    RESULT = {'changed_keys': len(changed), 'lying_keys_now': keys}
