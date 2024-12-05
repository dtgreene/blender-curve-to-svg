Simple Blender script for converting selected 2D curve objects into SVGs.
This was based on the [blender-curve-to-svg](https://github.com/aryelgois/blender-curve-to-svg) extension which no longer seems to work.

## Usage
1. Open the scripting tab.
2. Paste in the script.
3. Change the output path and any other values as needed.
4. Select the curves you want to convert and run the script.

### Some important notes:
- There's no support for NURBS curve types since there hasn't been a need yet.
- Disable `enable_auto_fit` when dimensionsal accuracy is important.  Auto-fit automatically scales and centers the image to fit within a target set of dimensions.  With auto-fit disabled, only the base transformations (y-flip and resetting the origin) will be applied.
- The curve type must be set to 2D.
- Location, rotation, and scale transformations must be applied first (while the curve is in 3D mode).

![image](https://github.com/user-attachments/assets/55b6a648-01b3-41f2-b595-45b2e57b1874)
