"""Secure connections.

Python normally checks website certificates with its own list. On many PCs that fails, because an
antivirus ("HTTPS scanning"), a company/university network or a VPN puts its own certificate in between,
which Windows/macOS trust but Python doesn't. With the `truststore` package (installed by setup), Python
asks Windows/macOS itself to check certificates, exactly like your browser does.
Certificate checking is NEVER switched off.
"""
import ssl

try:
    import truststore
    truststore.inject_into_ssl()
    SYSTEM_TRUST = True
except Exception:  # not installed (e.g. old Python) -> Python's normal checking
    SYSTEM_TRUST = False

CERT_HELP = ("Secure connection refused: something on this computer or network replaces the security "
             "certificates (often antivirus 'HTTPS/web scanning', a company/school network or a VPN). "
             "Fix: run the setup again (it installs 'truststore' so Python trusts the same certificates as your "
             "browser). If it still fails: turn off 'HTTPS scanning' in your antivirus, or try another network.")


def context():
    """Verified TLS context for mail (IMAP) connections."""
    return ssl.create_default_context()


def is_cert_error(e):
    """True if a connection failed because the certificate couldn't be verified
    (also when wrapped by urllib, or reported in the operating system's own words via truststore)."""
    seen = 0
    while e is not None and seen < 5:
        if isinstance(e, ssl.SSLCertVerificationError):
            return True
        text = str(e)
        if "CERTIFICATE_VERIFY_FAILED" in text or "certificate is not trusted" in text or "certificate chain" in text:
            return True
        e = getattr(e, "reason", None) or e.__cause__ or e.__context__
        seen += 1
    return False
