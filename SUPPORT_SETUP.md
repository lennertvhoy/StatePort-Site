# Support link setup

StatePort uses a plain external Ko-fi link. The site does not load a Ko-fi
widget, third-party JavaScript, tracking code, or visitor-side configuration.

The current repository configuration is deliberately fail closed. No Ko-fi
destination has been supplied and no account settings have been verified, so
the public support links are not rendered.

## Owner setup

1. Create or select the Ko-fi page that is owned by StatePort.
2. Keep the account on Ko-fi Free, disable Contributor mode, enable one-time
   tips, and do not add memberships, gated posts, or supporter obligations for
   this slice. Configure the payment account and currency directly in Ko-fi;
   never put payment credentials in this repository.
3. Confirm those external settings yourself. This static repository cannot
   inspect or prove the Ko-fi account configuration.
4. Set `publicUrl` in `config/support.json` to the direct public page. It must
   be an HTTPS `ko-fi.com` URL without a query or fragment.
5. Set `settingsAttested` to `true` only after confirming step 2.
6. Run:

   ```sh
   python3 scripts/render_support.py
   python3 scripts/validate_repo.py
   python3 scripts/check_site_quality.py
   ```

The renderer adds the same accessible external destination to the homepage
support section and footer. If the URL is absent, malformed, or not accompanied
by the explicit settings attestation, the renderer exposes no public link.
