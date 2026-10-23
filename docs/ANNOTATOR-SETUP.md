# SegQueue: getting set up as an annotator

Welcome to the team. This page gets SegQueue running on your computer and walks
you through your first case. It takes about 30 minutes, most of it download time.

You will need:

- Your username and password. The project lead sends these to you.
- The server address: `https://janus.bradensbay.com`
- A mouse with a scroll wheel. Segmenting with a trackpad is slow and tiring.

You do not need admin rights or any technical tools. If a step does not look like
what you see on screen, stop and ask the project lead. A screenshot helps.

---

## Windows

### Step 1. Install 3D Slicer

1. Go to https://download.slicer.org and open the older releases page.
2. Download **Slicer 5.8.1** for Windows and run the installer. Accept the defaults.
3. If a blue box says "Windows protected your PC", click **More info**, then
   **Run anyway**. Windows shows that for any program it has not seen often.
4. Start Slicer once from the Start menu. The first start takes a minute.

### Step 2. Install the Draw tube tool

1. In Slicer, open **View**, then **Extensions Manager**.
2. Search for **SegmentEditorExtraEffects** and click **Install**.
3. Restart Slicer when it asks.

### Step 3. Install SegQueue

1. Open https://github.com/christianGRogers/Asclepius/releases in your browser.
2. Under the newest release, download the file named
   `SegQueue-<version>-Slicer-5.8.zip`. Leave it as a zip file.
3. In Slicer, open **View**, then **Extensions Manager**.
4. Click **Install from file**, choose the zip you downloaded, and restart Slicer.

Now skip to **Logging in** below.

---

## Mac

### Step 1. Install 3D Slicer

1. Go to https://download.slicer.org and open the older releases page.
2. Download **Slicer 5.8.1** for macOS.
3. Open the downloaded file and drag **Slicer** into your **Applications** folder.
4. Start Slicer from Applications. If your Mac says the app is from an unidentified
   developer, right-click the Slicer icon, choose **Open**, and confirm. You only
   do this once.
5. If your Mac offers to install **Rosetta**, accept. Slicer runs fine with it.

### Step 2. Install the Draw tube tool

1. In Slicer, open **View**, then **Extensions Manager**.
2. Search for **SegmentEditorExtraEffects** and click **Install**.
3. Restart Slicer when it asks.

### Step 3. Install SegQueue

On a Mac, you add SegQueue as a folder rather than a zip. This works on every
version of Slicer, and it does not matter if Safari unzips the download for you.

1. Open https://github.com/christianGRogers/Asclepius/releases in your browser.
2. Under the newest release, download the file named
   `SegQueue-<version>-Slicer-5.8.zip` (the one **without** `macOS` in its name).
3. If the download is still a zip, double-click it. You now have a folder called
   **SegQueue**.
4. Move the SegQueue folder out of Downloads into your home folder or Documents,
   somewhere you will not delete by accident.
5. In Slicer, open **Edit**, then **Application Settings**, then click **Modules**
   on the left.
6. Next to **Additional module paths**, click **Add**. Open the SegQueue folder,
   then **lib**, then **Slicer-5.8**, and select the folder named
   **qt-scripted-modules**. Click **Open**.
7. Click **OK** and restart Slicer.

If you ever install a different version of Slicer, repeat steps 5 to 7 in it.

---

## Logging in

1. In Slicer, open the module list (the dropdown at the top), go to
   **Segmentation**, and choose **SegQueue**.
2. Check that the **Server** box says exactly `https://janus.bradensbay.com`. If
   it shows anything else, delete it and type that address. Slicer remembers it.
3. Enter your username and password and click **Log in**.

If you see "Update the SegQueue14 module", click **Check for updates** and then
**Update and restart**, then log in again.

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
3. In the Segment Editor, show one vessel at a time (click the eye next to its
   name) and erase everything that is not that vessel. Add any artery the outline
   missed, remove anything that is not a coronary artery, and keep the outline on
   the bright, contrast-filled part of the vessel.
4. Side branches belong to the vessel they come off. Diagonals and septals go with
   the LAD. Obtuse marginals go with the LCx. A ramus intermedius always goes with
   the LCx. A posterior descending or posterolateral branch goes with whichever
   artery it comes from.
5. Click **Submit case**. SegQueue will not let you submit if LAD, LCx or RCA is
   empty, or if any spot belongs to two vessels at once. It tells you which.

Useful buttons:

- **Save draft** keeps your work so you can carry on later.
- **Give this case back** returns a case you cannot finish.

Nothing is stored on your computer once a case is submitted.

## Keeping SegQueue up to date

Each time you open SegQueue it checks for a newer version. When one exists it
offers **Update and restart**. Click it. That is the whole update.

## If something goes wrong

| What you see | What to do |
|---|---|
| "Failed to copy directory" while installing | You are not on Slicer 5.8.1. Use the Mac steps (the folder method), which work on any version |
| The Server box shows an address ending in `example.edu` | Replace it with `https://janus.bradensbay.com` |
| "Could not reach the server" | Check your internet connection and the Server box |
| SegQueue says Draw tube is missing | Go back to Step 2 and install SegmentEditorExtraEffects |
| SegQueue is not in the module list (Mac) | Check the folder you added ends in `qt-scripted-modules`, then restart Slicer |
| "Cannot submit" | Read the message. Either a required vessel is empty, or two vessels overlap somewhere |

Still stuck? Send the project lead a screenshot, your Slicer version (**Help**,
then **About 3D Slicer**), and whether you are on Windows, an Intel Mac or an
Apple chip Mac.
