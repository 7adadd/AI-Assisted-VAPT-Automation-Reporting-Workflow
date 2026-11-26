/*
 * Frida SSL Pinning Bypass (Android TrustManager + OkHttp3 CertificatePinner)
 * Generated via prompt M2 (qwen2.5:3b) from ai-M2-ssl-qwen.md.
 *
 * Human L2 QA fixes (logged in evidence/validation-log.md):
 *  - Raw AI hallucinated `android.net.http.SSLCertificateSocketFactory$TrustManager.onGetCertificateChain`
 *    and `okhttp3.OkHttp$CertificatePinner.pinToKeyStore`.
 *  - Replaced with genuine Android AOSP `javax.net.ssl.X509TrustManager` / `SSLContext.init`
 *    and `okhttp3.CertificatePinner.check(String, List)` hooks.
 *
 * Usage: frida -U -f jakhar.aseem.diva -l scripts/generated/frida_ssl_pinning_bypass.js
 */
Java.perform(function () {
    console.log("[Frida] Initializing SSL Pinning Bypass...");

    // 1. Standard Android SSLContext / X509TrustManager bypass
    try {
        var X509TrustManager = Java.use("javax.net.ssl.X509TrustManager");
        var SSLContext = Java.use("javax.net.ssl.SSLContext");

        var TrustManager = Java.registerClass({
            name: "dev.vapt.BypassTrustManager",
            implements: [X509TrustManager],
            methods: {
                checkClientTrusted: function (chain, authType) {},
                checkServerTrusted: function (chain, authType) {},
                getAcceptedIssuers: function () { return []; }
            }
        });

        var TrustManagers = [TrustManager.$new()];
        SSLContext.init.overload(
            "[Ljavax.net.ssl.KeyManager;",
            "[Ljavax.net.ssl.TrustManager;",
            "java.security.SecureRandom"
        ).implementation = function (km, tm, sr) {
            console.log("[Hook] SSLContext.init intercepted -> injecting permissive TrustManager");
            this.init(km, TrustManagers, sr);
        };
    } catch (e) {
        console.log("[Warn] SSLContext hook skipped: " + e);
    }

    // 2. OkHttp3 CertificatePinner bypass (if app bundles OkHttp3)
    try {
        var CertificatePinner = Java.use("okhttp3.CertificatePinner");
        CertificatePinner.check.overload("java.lang.String", "java.util.List").implementation = function (host, certs) {
            console.log("[Hook] OkHttp3 CertificatePinner.check bypassed for: " + host);
            return;
        };
    } catch (e) {
        console.log("[Info] OkHttp3 CertificatePinner not present in target: " + e);
    }
});
