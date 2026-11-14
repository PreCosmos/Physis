import bpy,numpy as np
im=bpy.data.images.load("/var/home/precosmos/Έγγραφα/Unreal Projects/Physis/Art/Meshes/Kit/Textures/T_KitDecal_BaseColor.png")
p=np.array(im.pixels[:]).reshape(2048,2048,4)
print('ALPHA',p[...,3].min(),p[...,3].mean(),p[...,3].max(),'RGB',p[...,:3].mean(),im.alpha_mode,im.channels,im.depth)
