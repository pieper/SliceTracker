# Intra-procedural tracking of targets

Intra-procedural phase of the workflow is driven by the intra-procedural image data. The sequence of processing steps and the corresponding types of image series is the following:
1. Z-frame calibration: in this step, z-frame device attached to the transperineal biopsy template is registered with the coordinate frame of the scanner. In AMIGO, Z-frame image series will have the name "AX TSE T2 COVER TEMPLATE".
2. Registration of the pre-procedural T2-weighted series to the intra-procedural imaging and re-identification of the planned target locations. In AMIGO, initial, high-resolution intra-procedural T2-weighted image will have the name "AXIAL T2 COVER PROSTATE".
3. Tracking of the biopsy targets in the needle confirmation scans and visualization of the needle path. In AMIGO, needle confirmation images will be called either "AX TSE T2 GUIDANCE FOR NEEDLE" (T2-weighted images) or "AX 3D VIBE".

## Z-frame calibration

Z-frame is a calibration device that consists of a plastic enclosure that attaches rigidly to the template assembly, and 7 elongated capsules containing liquid that gives bright signal in certain types of MR images. 

Given the known configuration of these capsules and their appearance in the image, it is possible to align the known configuration with the corresponding image artifacts, and thus establish a transformation between the biopsy template and the scanner coordinate system.

| ![Biopsy template assembly (left) and z-frame. MR-visible capsules are of yellow color within a plexiglass enclosure.](../images/zframe.png) | ![Z-frame and needle template models before calibration ](../images/zframe_unregistered_annotated.png) |
| -- | -- |
| Biopsy template assembly (left) and z-frame. MR-visible capsules are of yellow color within a plexiglass enclosure. | Z-frame (yellow arrow) and needle tracks of the template (blue arrow) models before calibration. Red arrow points to the artifacts corresponding to the z-frame in the image slice. |

Once z-frame is received, it will be automatically loaded and displayed. To perform z-frame calibration, you will need to define the region of interest (ROI) in the image corresponding to the location of the z-frame artifacts. ROI placement mode will be activated automatically once z-frame image is loaded, and the mouse pointer icon  ![](../images/roi_icon.png) will reflect this. 

With the ROI mode enabled, click once in the center of the group of bright dots corresponding to the z-frame, and once in the corner just outside that group. Make sure all dots are within the rectangular selection area, as shown in the figure below (arrows indicate the center and corner where you would click to define the ROI).

![](../images/zframe_roi.png)

Once you confirm that all dots are within the ROI, click "Run ZFrame Registration" in the module control panel.

Once z-frame calibration is completed, 3D viewer will show the co-registered position of the image. 

**IMPORTANT**: Verify that z-frame calibration was completed correctly by confirming the alignment of the z-frame model with the z-frame image artifacts, both in 2D and 3D views. In the 2D view, intersections of the z-frame model with the image will be indicated by yellow outlines. Those must closely follow the bright artifacts of the z-frame, as shown in the figure below. If you are unsure, please confirm with the clinical lead of the procedure!

![](../images/zframe_verification.png)

You must confirm registration accuracy by clicking "Confirm registration accuracy" button in the SliceTracker panel in order to proceed with the next steps of the workflow.

## Cover prostate registration and re-identification of the planned targets

Once z-frame registration is confirmed, and cover prostate image is acquired, the grid of the needle paths of the template will be shown in overlay of the cover prostate image.

**IMPORTANT**: Notify the clinical lead of the procedure once you reach this point. This is important to confirm coverage of the gland.

After coverage is confirmed, proceed with target re-identification by clicking "Track targets" button.

To track targets, you will first prepare a rough segmentation of the prostate gland. Your mouse cursor should automatically show fiducial placement icon ![](../images/fiducialmode_icon.png). 

Click in the vicinity of the prostate capsule boundary to make sure the green outline approximates the capsule. You will need to place points on multiple slices before the green outline appears.

Buttons in the module panel provide the following features:
* <img src="../../SliceTracker/Resources/Icons/icon-greenCheck.png" width="20">: finish segmentation
* <img src="../../SliceTracker/Resources/Icons/icon-undo.png" width="20">  <img src="../../SliceTracker/Resources/Icons/icon-redo.png" width="20">: undo/redo pont placement
* <img src="../../SliceTracker/Resources/Icons/icon-cancelSegmentation.png" width="20">: cancel segmentation

After completing segmentation result, layout will automatically change to show the pre-procedural (planning) T2-weighted image on the left, and the intra-procedural image on the right, with the segmentation overlays in both viewers. Confirm that segmentations are similar (no large portions of the gland are skipped in either of the images).

Click "Apply registration" once segmentation consistency is confirmed.

Upon completion of registration, you will be presented with a layout showing biopsy plan on the left, and registration result on the right.

**IMPORTANT**: Confirm the accuracy of registration with the clinical lead of the procedure!

You can use the following tools to verify registration accuracy:
* "Rock": slowly fade back and forth between the registered planning image and the cover prostate image.
* "Flicker": quickly flip back and forth between the registered planning image and the cover prostate image.
* "Reveal cursor" button: show mosaic of the registered planning image and the cover prostate image at the cursor location.

| ![Biopsy template assembly (left) and z-frame. MR-visible capsules are of yellow color within a plexiglass enclosure.](../images/registration_evaluation.png) | ![Z-frame and needle template models before calibration ](../images/reveal_cursor.png) |
| -- | -- |
| User interface elements to support registration result evaluation. | Reveal cursor in action. |


**If registration result is satisfactory**: Click "Approve", communicate the needle hole and insertion depth to the clinical lead.

**If registration result is NOT satisfactory**, here is what you can try:
* _check different registration types (Rigid or Affine)_: if any of these is satisfactory - approve it.
* _move the target to a more suitable location_: double-click the corresponding target row in the target table, which will toggle target move mode. You can then scroll to the desired slice for the target, and place on the updated location.
* _re-do segmentation of the prostate and re-run registration_: this can be done by clicking "Retry" button. Note that this approach is most time-consuming.

## Tracking targets in the needle confirmation images

SliceTracker will detect arrival of new needle images automatically, and will alert the operator asking whether tracking should be done automatically for new images. SliceTracker will attempt to perform registration automatically, and will provide the same evaluation interface as for the cover prostate registration step. 

When needle confirmation registration fails, this is most often due to very large motion of the prostate/patient. If such large motion is observed, it is advised that prostate is re-segmented in the needle confirmation image.

Once registration to needle confirmation is completed:
* any updates to the hole/insertion depth for the individual targets will be indicated by bright red highlight of the corresponding cells in the target table. Previous location of the hole/depth can be obtained in tooltips for the updated cells.
* the clinical lead of the procedure will typically be interested in the location of the needle relative to the intended target. To help with this task, switch to the FourUp layout ![](../../SliceTracker/Resources/Icons/icon-four-up.png) and turn on crosshair ![](../../SliceTracker/Resources/Icons/icon-crosshair.png). Follow the needle track in one of the slice viewers while holding the Shift button. This will synchronize all viewers locations.