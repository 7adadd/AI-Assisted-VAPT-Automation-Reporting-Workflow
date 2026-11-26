/*
 * Frida DIVA Runtime Hook (HardcodeActivity.access & LogActivity.processCC)
 * Generated via prompt M2 (qwen2.5:3b) from ai-M2-diva-qwen.md.
 *
 * Verified against decompiled DIVA classes in evidence/week3/diva-src/:
 *  - jakhar.aseem.diva.HardcodeActivity.access(android.view.View)
 *  - jakhar.aseem.diva.LogActivity.processCC(java.lang.String)
 *
 * Human L2 QA fixes:
 *  - Removed redundant nested Java.perform() calls inside Java.perform().
 *  - Fixed `this.access.call(this, view)` -> `this.access(view)` (Frida JS method invocation).
 *
 * Usage: frida -U -f jakhar.aseem.diva -l scripts/generated/frida_diva_hardcode_hook.js
 */
Java.perform(function () {
    try {
        var HardcodeActivity = Java.use("jakhar.aseem.diva.HardcodeActivity");
        HardcodeActivity.access.overload("android.view.View").implementation = function (view) {
            console.log("[Hook] HardcodeActivity.access(View) invoked");
            return this.access(view);
        };
        console.log("[Frida] Attached to jakhar.aseem.diva.HardcodeActivity.access");
    } catch (e) {
        console.error("[Frida] HardcodeActivity hook error: " + e);
    }

    try {
        var LogActivity = Java.use("jakhar.aseem.diva.LogActivity");
        LogActivity.processCC.overload("java.lang.String").implementation = function (ccstr) {
            console.log("[Hook] LogActivity.processCC intercepted input: " + ccstr);
            return this.processCC(ccstr);
        };
        console.log("[Frida] Attached to jakhar.aseem.diva.LogActivity.processCC");
    } catch (e) {
        console.error("[Frida] LogActivity hook error: " + e);
    }
});
