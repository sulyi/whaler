This prototype highlights the possible use of an armature  
created in `Blender`, and uses [`Panda3d`][1] engine. The  
original model was downloaded from [www.cadnav.com][2].

The format used by the engine for the 3d models handles  
only the bone joint. Therefore before exporting extra  
"tail bones" has to be added to some bones in order to  
create a joint at the tail of those bones. This  
demonstration also solves that the used format does not  
handle bone constraints.

The armature is controlled 3-5 bones per yard, a single  
bone controls the yard and 2 or 4 other bones serve as an  
anchor for the braces. There are 3, 2, or a single deform  
bone(s) per brace depending on whether the two lines  
running over the pulley are anchored to different points  
or not and if there is a pulley at all.

The anchor bones can be moved or rotated and the  
controlled brace will follow them or an interpolated value  
between the two control bones. The yard control bone can  
be moved rotated and the yard will follow the position and  
rotation as well, but when the control bone is scaled  
only the tips of the yard will move in the y-axes,  
therefore bending the yard. 

Controls
--------
    
   * space:
       - shows hud to select action and target
   * shift:
       - unlocks camera
   * mouse wheel:
       - dolly camera (if unlocked),
       - action on 3rd axis (else)
   * left mouse:
       - action in 1st and 2nd axises

Todo
----

   * Keyboard control (optional).
   * `Rigify` meta-rig for `Blender` and script creating  
     armature from meta-rig

[1]: https://www.panda3d.org/
[2]: http://www.cadnav.com/
