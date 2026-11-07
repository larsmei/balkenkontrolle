# Orientation

The local frame follows Code_Aster, document U4.42.01, for a straight SEG2.

Local X points from the first node to the second.

Without `ORIENTATION`, the angle is `ANGL_VRIL = 0`.

If the beam is not parallel to global Z, local Y is `normalize(global Z × local X)` and local Z completes the right-handed frame. A horizontal beam then has local Z pointing up.

If the beam is parallel to global Z, local Y is parallel to global Y. The log says so.

`VECT_Y` and `VECT_Z` replace that default. The vector is projected onto the plane normal to the beam. The projection becomes Y or Z. A vector parallel to the beam has a zero projection. Code_Aster rejects it, and the plugin keeps the default frame and writes a note.

`ANGL_VRIL` rotates the default frame right-handed about X. The unit is degrees.

`VECT_MAIL_Y` and `VECT_MAIL_Z` are shown as the mesh direction only. The angle between the fibre mesh and the principal axes from `MACR_CARA_POUTRE` is not applied.

On screen, X is red, Y is green, Z is blue.
