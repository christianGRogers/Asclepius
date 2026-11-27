# SegQueue: getting set up as an annotator

Welcome to the team. This page gets SegQueue running on your computer and walks
you through your first case. It takes about 30 minutes, most of it download time.

You will need:

- Your username and password. The project lead sends these to you.
- The server address: `https://janus.bradensbay.com`
- A mouse with a scroll wheel. Segmenting with a trackpad is slow and tiring.

You do not need admin rights or any technical tools. If a step does not look like
what you see on screen, stop and ask the project lead. A screenshot helps.

Pick your system: [Windows](#windows) or [Mac](#mac). Both paths install the same
three things, in this order: 3D Slicer 5.8.1, the Draw tube extension, then the
SegQueue extension.

---

## Windows

### Step 1. Install 3D Slicer 5.8.1

SegQueue needs Slicer version **5.8.1** exactly. The big download buttons on the
Slicer site give you a newer version, so use the older releases list instead.

1. Go to https://download.slicer.org.
2. Under **Stable Release**, click the small link **access older releases**.

   ![The download page, with the access older releases link under Stable Release](images/annotator/slicer-download-page.png)

3. In the first dropdown choose **Slicer 5.8.1**, in the second choose
   **Windows**, and click **Download**.

   ![Older releases picker set to Slicer 5.8.1 and Windows](images/annotator/slicer-download-windows.png)

4. Run the installer and accept the defaults.
5. If a blue box says "Windows protected your PC", click **More info**, then
   **Run anyway**. Windows shows that for any program it has not seen often.
6. Start Slicer once from the Start menu. The first start takes a minute.

### Step 2. Install the Draw tube extension

1. In Slicer, open **View**, then **Extensions Manager**.
2. Search for **SegmentEditorExtraEffects** and click **Install**.

   ![Extensions Manager showing SegmentEditorExtraEffects with its Install button](images/annotator/extensions-manager-extraeffects.png)

3. Restart Slicer when it asks.

### Step 3. Install the SegQueue extension

1. Open https://github.com/christianGRogers/Asclepius/releases/latest in your
   browser and scroll down to **Assets**.
2. Download the file named `SegQueue-<version>-Slicer-5.8.zip`, the one
   **without** `macOS` in its name. Leave it as a zip file.

   ![The Assets list on the release page with the two SegQueue zips](images/annotator/release-assets.png)

3. In Slicer, open **View**, then **Extensions Manager**.
4. Click **Install from file** at the bottom of the window, choose the zip you
   downloaded, and restart Slicer.

   ![Extensions Manager with the Install from file button at the bottom](images/annotator/extensions-manager.png)

Now skip to [Logging in](#logging-in).

---

## Mac

### Step 1. Install 3D Slicer 5.8.1

SegQueue needs Slicer version **5.8.1** exactly. The big download buttons on the
Slicer site give you a newer version, so use the older releases list instead.
Slicer 5.8.1 comes as an Intel build only. It runs on Apple chip Macs (M1, M2,
M3, M4) through Rosetta, which your Mac offers to install the first time.

1. Go to https://download.slicer.org.
2. Under **Stable Release**, click the small link **access older releases**.

   ![The download page, with the access older releases link under Stable Release](images/annotator/slicer-download-page.png)

3. In the first dropdown choose **Slicer 5.8.1**, in the second choose
   **macOS Intel (amd64)**, and click **Download**. This is the right choice on
   every Mac, Intel or Apple chip.

   ![Older releases picker set to Slicer 5.8.1 and macOS Intel](images/annotator/slicer-download-mac.png)

4. Open the downloaded `.dmg` file and drag **Slicer** into your **Applications**
   folder.
5. Start Slicer from Applications. If your Mac says the app is from an unidentified
   developer, right-click the Slicer icon, choose **Open**, and confirm. You only
   do this once.
6. If your Mac offers to install **Rosetta**, accept. Slicer runs fine with it.

### Step 2. Install the Draw tube extension

1. In Slicer, open **View**, then **Extensions Manager**.
2. Search for **SegmentEditorExtraEffects** and click **Install**.

   ![Extensions Manager showing SegmentEditorExtraEffects with its Install button](images/annotator/extensions-manager-extraeffects.png)

3. Restart Slicer when it asks.

### Step 3. Install the SegQueue extension

SegQueue installs through the Extensions Manager from a zip file, the same way as
on Windows. The one Mac wrinkle is Safari: by default it unzips every zip it
downloads, and Slicer needs the zip itself. Turn that off first.

1. **If you use Safari**, do one of these. Either open **Safari**, then
   **Settings**, then the **General** tab, and untick **Open "safe" files after
   downloading** (you can turn it back on afterwards). Or leave the setting alone
   and, in step 3, right-click the file name (Control-click, or a two-finger click
   on a trackpad) and choose **Download Linked File As**, which keeps it as a zip.
   If you use Chrome or Firefox, skip this step.
2. Open https://github.com/christianGRogers/Asclepius/releases/latest in your
   browser and scroll down to **Assets**.
3. Download the file named `SegQueue-<version>-Slicer-5.8-macOS.zip`, the one
   **with** `macOS` in its name. Leave it as a zip file.

   ![The Assets list on the release page with the two SegQueue zips](images/annotator/release-assets.png)

4. Look in your Downloads folder. You should see the `.zip` file. If instead you
   see a folder called **SegQueue**, Safari unzipped it: delete that folder, do
   step 1, and download again.
5. In Slicer, open **View**, then **Extensions Manager**.
6. Click **Install from file** at the bottom of the window, choose the zip you
   downloaded, and restart Slicer.

   ![Extensions Manager with the Install from file button at the bottom](images/annotator/extensions-manager.png)

---

## Logging in

1. In Slicer, open the module list (the dropdown at the top of the window), go to
   **Segmentation**, and choose **SegQueue**.

   ![The module dropdown open at Segmentation, with SegQueue in the submenu](images/annotator/module-menu.png)

2. Check that the **Server** box says exactly `https://janus.bradensbay.com`. If
   it shows anything else, delete it and type that address. Slicer remembers it.
3. Enter your username and password and click **Log in**.

   ![The SegQueue panel with the Server box and the login fields](images/annotator/segqueue-panel.png)

If you see "Update the SegQueue14 module", click **Check for updates** and then
**Update and restart**, then log in again. Reviewers: "Update SegQueue14 to review
this read" means the same thing. That read uses the extended classes, which older
versions cannot show.

## Your first case

1. Click **Get next case**. A CT scan loads with a yellow outline of the coronary
   arteries. The outline is automatic and rough. Your job is to turn it into four
   clean, correctly named vessels.
2. The four vessels are:

   | Name | Vessel | Must be filled in |
   |---|---|---|
   | LM | Left main | No (some people have none) |
   | LAD | Left anterior descending | Yes |
   | LCx | Left circumflex | Yes |
   | RCA | Right coronary artery | Yes |

   Each one starts as a hidden copy of the yellow outline.
3. In the Segment Editor, work on one vessel at a time: click its name to select
   it, which also shows it (from SegQueue 0.25.4; the other classes stay as they
   are, and the eye next to each name still hides or shows it). Erase everything
   that is not that vessel. Add any artery the outline
   missed, remove anything that is not a coronary artery, and keep the outline on
   the bright, contrast-filled part of the vessel.
4. Side branches belong to the vessel they come off. Diagonals and septals go with
   the LAD. Obtuse marginals go with the LCx. A ramus intermedius always goes with
   the LCx. A posterior descending or posterolateral branch goes with whichever
   artery it comes from.
5. Click **Submit case**. Nothing checks what you drew before it is sent, so look
   over each vessel yourself first.

### Inverse cut

Next to Scissors in the Segment Editor there is an **Inverse cut** tool (yellow
shape with scissors). Use it to keep a small part instead of erasing everything
around it. Select a class, click Inverse cut, then hold the left mouse button and
draw around the part you want. When you let go, the class keeps only what is inside
your outline, through every slice, like Scissors does. If the class is empty, it
gets the part of the yellow outline that is inside your shape instead. No other
class changes. **Ctrl+Z** undoes it.

### Extended classes (optional)

Above the Segment Editor there is a box called **Extended classes**. It
is off unless you turn it on, and SegQueue remembers your choice for your login.
If you leave it off, everything above is the whole job.

Turned on, it adds 17 more classes, listed under the vessel they belong to. On a
case with the yellow outline, a branch class becomes a copy of it the first time
you select it, just like the four vessels start (from SegQueue 0.25.4; before that,
all of them were copied when the box was turned on, which was slow). If you then
erase it, it stays erased. Stent, calcified plaque and non-calcified plaque always
start empty, on every case. On a case without the outline, every extended class
starts empty:

| Group | Classes |
|---|---|
| LAD branches | D1, D2, D3 (1st to 3rd diagonal); S1, S2, S3 (1st to 3rd septal) |
| LCx branches | OM1, OM2 (1st and 2nd obtuse marginal) |
| Other | Ramus (ramus intermedius) |
| RCA branches | SN (sinus node), Conus, RMA (right marginal), PDA, PLB (posterolateral) |
| Materials | Stent, Calcified plaque, Non-calcified plaque |

- Use only the ones you want. An empty class is fine. If you leave a branch class
  as an untouched copy of the outline, it is sent empty.
- To use a branch class, move that branch out of whichever vessel it leaves and
  into its class. For example, erase the first diagonal from LAD and paint it into
  D1. SN, PDA and PLB come out of the RCA or the LCx, whichever they come off: in
  a left-dominant heart the PDA and PLB come off the LCx.
- Trace septals, SN, conus and RMA as far as you can see them, even where the
  vessel seed stops.
- Some cases open with the box already on and a note asking you to use the
  extended classes. Please do.
- Paint stent and plaque where you see them, starting from an empty class. They
  may overlap the vessel. From SegQueue 0.25.4 the editor keeps both: under **Masking**, *Modify other segments*
  is **Allow overlap** whenever a case opens, also in Slicer's own Segment Editor
  module. If you change it, it stays changed until the next case.
- Hover over a group name in the box to see what goes in each class. The
  **Show** ticks hide or show a whole group.
- Turning the box off only hides the extended classes. Nothing is deleted, and
  turning it back on shows them exactly as they were (from SegQueue 0.25.6). You do
  not need to turn it off before you submit: if any extended class has your work in
  it, or the case asked for the extended classes,
  it is sent with all 21 classes, whether the box is on or off. Otherwise (the
  classes are empty, or untouched copies of the outline) it is sent with the four.

Useful buttons:

- **Save draft** keeps your work so you can carry on later.
- **Give this case back** returns a case you cannot finish.
- **Discard changes and close** takes its place on a case you took back from **My
  submissions** with **Revise**. Your submission goes back for review exactly as you
  submitted it.

Nothing is stored on your computer once a case is submitted.

## Keeping SegQueue up to date

Each time you open SegQueue it checks for a newer version. When one exists it
offers **Update and restart**. Click it. That is the whole update. You never need
to download a zip again.

## If something goes wrong

| What you see | What to do |
|---|---|
| "Failed to copy directory" while installing | You are on a newer Slicer than 5.8.1. Go back to Step 1 and install 5.8.1 from the older releases list, then install the zip again |
| A folder called SegQueue appeared instead of a zip (Mac) | Safari unzipped the download. Delete the folder, then either turn off "Open safe files" in Safari settings or right-click the file name and choose Download Linked File As, and download again |
| Install from file does not list your download | The file picker only shows zip files. If you only see a folder, see the row above |
| The Server box shows an address ending in `example.edu` | Replace it with `https://janus.bradensbay.com` |
| "Could not reach the server" | Check your internet connection and the Server box |
| SegQueue says Draw tube is missing | Go back to Step 2 and install SegmentEditorExtraEffects |
| SegQueue is not in the module list | Make sure you restarted Slicer after installing. If it is still missing, install the zip again |
| "Cannot submit" | Read the message. It is about your login, the case or the upload, never about what you drew: since 2026-11-02 empty vessels no longer block a submit, so check them yourself first |

Still stuck? Send the project lead a screenshot, your Slicer version (**Help**,
then **About 3D Slicer**), and whether you are on Windows, an Intel Mac or an
Apple chip Mac.
