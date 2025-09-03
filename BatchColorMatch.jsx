// === BATCH MATCH COLOR (Original Images -> Upscaled Images -> Result) ===
// Uses a recorded Photoshop action to "match color" from a reference file
// to a target file with the SAME BASENAME. Extensions may differ.
// Basename matching also ignores trailing " - x of y" copy suffixes.
//
// Folders (auto):
//   <Project Root>\Original Images   (reference / correct colors)
//   <Project Root>\Upscaled Images   (target / needs correction)
//   <Project Root>\Result            (output; auto-created)
//
// IMPORTANT: Set the action set/name to your recorded Match Color step.
// The action should expect the TARGET to be active, with the REFERENCE
// document open in Photoshop. We open both for each file.
// -----------------------------------------------------------------------

#target photoshop
app.displayDialogs = DialogModes.NO;

(function () {
    // ---- Configure your action here ----
    var ACTION_SET  = "Default Actions";      // <-- change to your set
    var ACTION_NAME = "MatchColorFromRef";    // <-- change to your action

    // ---- Select project root one time, auto-locate subfolders ----
    var root = Folder.selectDialog("Select your PROJECT ROOT (containing 'Original Images' and 'Upscaled Images')");
    if (!root) { alert("Cancelled."); return; }

    var refFolder = Folder(root.fsName + "/Original Images");
    var tgtFolder = Folder(root.fsName + "/Upscaled Images");
    var outFolder = Folder(root.fsName + "/Result");

    if (!refFolder.exists) { alert("Missing folder: " + refFolder.fsName); return; }
    if (!tgtFolder.exists) { alert("Missing folder: " + tgtFolder.fsName); return; }
    if (!outFolder.exists) { outFolder.create(); }

    // ---- Helpers ----
    function listImages(folder) {
        return folder.getFiles(function (f) {
            if (f instanceof File) {
                var n = f.name.toLowerCase();
                return /\.(png|jpg|jpeg|tif|tiff|psd)$/i.test(n);
            }
            return false;
        });
    }
    function stripCopySuffix(nameNoExt) {
        // Remove trailing " - 2 of 3" like suffixes from our own per-deck copies
        return nameNoExt.replace(/\s*-\s*\d+\s+of\s+\d+\s*$/i, "");
    }
    function basenameNoExt(f) {
        var n = f.name.replace(/\.[^.]+$/, "");  // drop extension
        return stripCopySuffix(n).toLowerCase();
    }
    function savePNG(doc, outFile) {
        var opts = new PNGSaveOptions();
        opts.compression = 9;
        doc.saveAs(outFile, opts, true, Extension.LOWERCASE);
    }
    function safeClose(doc) {
        try { doc.close(SaveOptions.DONOTSAVECHANGES); } catch (e) {}
    }

    // ---- Build reference map by basename (case-insensitive) ----
    var refFiles = listImages(refFolder);
    if (!refFiles.length) { alert("No images found in: " + refFolder.fsName); return; }

    var refMap = {};
    for (var r = 0; r < refFiles.length; r++) {
        try {
            var key = basenameNoExt(refFiles[r]);
            // Prefer PNG/TIF/PSD over JPEG if multiple exist
            if (!refMap[key]) refMap[key] = refFiles[r];
            else {
                var cur = refMap[key].name.toLowerCase();
                var nxt = refFiles[r].name.toLowerCase();
                var rank = function (n) {
                    if (/\.psd$/.test(n)) return 0;
                    if (/\.tif$|\.tiff$/.test(n)) return 1;
                    if (/\.png$/.test(n)) return 2;
                    if (/\.jpg$|\.jpeg$/.test(n)) return 3;
                    return 9;
                };
                if (rank(nxt) < rank(cur)) refMap[key] = refFiles[r];
            }
        } catch (e) {}
    }

    var tgtFiles = listImages(tgtFolder);
    if (!tgtFiles.length) { alert("No images found in: " + tgtFolder.fsName); return; }

    var logFile = File(outFolder.fsName + "/BatchColorMatch.log");
    logFile.encoding = "UTF8";
    logFile.open("w");
    logFile.writeln("Batch Color Match log");
    logFile.writeln("Root: " + root.fsName);
    logFile.writeln("Reference: " + refFolder.fsName);
    logFile.writeln("Target: " + tgtFolder.fsName);
    logFile.writeln("Output: " + outFolder.fsName);
    logFile.writeln("Action: " + ACTION_SET + " / " + ACTION_NAME);
    logFile.writeln("---------------------------------------------");

    var processed = 0, missing = 0, failed = 0;

    for (var i = 0; i < tgtFiles.length; i++) {
        var tgtFile = tgtFiles[i];
        var key = basenameNoExt(tgtFile);
        var refFile = refMap[key];

        if (!refFile) {
            logFile.writeln("[MISSING REF] " + tgtFile.name + "  (no match in 'Original Images')");
            missing++;
            continue;
        }

        var docRef, docTgt;
        try {
            docRef = app.open(refFile);
            docTgt = app.open(tgtFile);

            // Ensure TARGET is active before running the action
            app.activeDocument = docTgt;

            // Run your recorded action (must reference the currently open REF doc)
            // If your action relies on a specific doc name, re-record it using
            // “Source: [document]” WITHOUT hard-coding the filename.
            app.doAction(ACTION_NAME, ACTION_SET);

            // Save as PNG in Result, preserving the target's basename
            var outFile = File(outFolder.fsName + "/" + tgtFile.name.replace(/\.[^.]+$/, "") + ".png");
            savePNG(docTgt, outFile);
            processed++;
        } catch (err) {
            logFile.writeln("[ERROR] " + tgtFile.name + " :: " + err);
            failed++;
        } finally {
            if (docTgt) safeClose(docTgt);
            if (docRef) safeClose(docRef);
        }
    }

    logFile.writeln("---------------------------------------------");
    logFile.writeln("Processed: " + processed + " | Missing refs: " + missing + " | Failed: " + failed);
    logFile.close();

    alert("Done.\nProcessed: " + processed + "\nMissing refs: " + missing + "\nFailed: " + failed + "\n\nLog: " + logFile.fsName);
})();
