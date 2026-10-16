# War Haven custom domain

The owner purchased `warhavenclan.com` on October 16, 2026. The intended main dashboard address is `https://warhavenclan.com/`, hosted by the existing `phil14-hub/war-haven-dashboard` GitHub Pages repository. Domain purchase does not activate the website or email delivery by itself.

The shared service accepts only its own origin and these dashboard origins: `https://phil14-hub.github.io`, `https://warhavenclan.com`, and `https://www.warhavenclan.com`. Current authentication, independent update queues and encrypted shared notes still apply. The member portal continues to use the existing shared-actions service.

## 1. Verify ownership in GitHub

Open https://github.com/settings/pages and choose **Add a domain**. Enter `warhavenclan.com`. Copy the exact TXT record GitHub generates into Spaceship's **Advanced DNS** for this domain, then click **Verify** in GitHub. Keep that TXT record afterward. Its value is account-specific; do not substitute a sample token.

## 2. Select the domain in GitHub Pages

Open https://github.com/phil14-hub/war-haven-dashboard/settings/pages. Keep **Deploy from a branch**, **main**, **/(root)**. Under **Custom domain**, save `warhavenclan.com` before pointing the domain's website records to GitHub. Do not change this repository to a custom Actions Pages build: the collectors expect branch-based Pages publication.

GitHub creates the root `CNAME` file for branch publication. The collectors preserve other repository files when publishing the two encrypted data files, so future updates retain this setting.

## 3. Point Spaceship DNS to GitHub

In Spaceship, open **Advanced DNS** and select `warhavenclan.com`. Keep its current Spaceship nameservers. Replace only the domain's existing parking/website A records with these records; preserve TXT and email records.

| Type | Host | Value |
| --- | --- | --- |
| A | @ | 185.199.108.153 |
| A | @ | 185.199.109.153 |
| A | @ | 185.199.110.153 |
| A | @ | 185.199.111.153 |
| CNAME | www | phil14-hub.github.io |

Use the default TTL. The CNAME target is the GitHub account hostname, with no `https://`, repository name or trailing path. Do not create wildcard records. At the initial check, the parking A records were `34.216.117.25` and `54.149.79.189`; check the current settings before replacing records.

## 4. Activate HTTPS and validate

DNS can take up to 24 hours to propagate. When GitHub's certificate is ready, enable **Enforce HTTPS**. Verify both the root and www address, the sign-in links, encrypted dashboard unlock, autosaved notes/plans and the two independent refresh buttons. A changed domain can require a fresh dashboard unlock because browser session storage is origin-specific.

The scheduled collectors and saved archive continue using the existing GitHub repository. The planned migration of the original archive out of Git history to R2 remains separate.

## 5. Activate account emails separately

Create the owner's free Resend account and add `warhavenclan.com`. Add the exact DNS records Resend supplies and wait for **Verified**. A paid inbox is not required to send as `War Haven <accounts@warhavenclan.com>`. Avoid purchasing a separate mail-hosting package just to enable these messages.

The shared-actions Site requires `RESEND_API_KEY` as a secret and `MAIL_FROM` as the verified sender. Enter the key through secure runtime environment settings rather than chat, repository files or logs. Redeploy the saved service version after setting these values. Registration remains closed until email sending is configured; verify actual email delivery and password recovery before inviting members.

## Official references

- https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site
- https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/verifying-your-custom-domain-for-github-pages
- https://resend.com/docs/dashboard/domains/introduction
