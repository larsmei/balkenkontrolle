# Cross-sections

Contours are built in the local yz plane. The origin is the centroid. Local Y points right and local Z points up when local X points towards the viewer.

## RECTANGLE

`HY` is the width along Y, `HZ` the height along Z. `EPY` is the wall thickness in Y (left and right walls), `EPZ` the thickness in Z (top and bottom). Missing thicknesses mean a solid section. If the walls fill the rectangle, the solid section is drawn and the log says so.

## CERCLE

`R` is the outer radius. `EP` smaller than `R` is a tube. Missing `EP`, or `EP` equal to `R`, is a solid circle. `EP` larger than `R` is drawn as a solid circle.

## GENERALE

`SECTION='GENERALE'` has no contour, only section properties. The drawing is a solid ellipse whose bending inertias are exactly the given `IY` and `IZ`.

`IY` is the moment about the local Y axis (∫ z² dA). `IZ` is the moment about the local Z axis (∫ y² dA). The semi-axis along Z follows from `IY`, the semi-axis along Y from `IZ`. `RY` and `RZ` are fibre distances and are not used as the contour. If `IY` or `IZ` is missing or not positive, only the axes are shown.

## COUDE

Elbows are drawn with the nominal section only. Ovalisation is not shown.

## What is not drawn

Shear areas `AY` and `AZ`, offsets `EY` and `EZ`, and the torsion constant `JX` do not change the contour. A variable section (`VARI_SECT`) is drawn with the dimensions at the start of the beam.
