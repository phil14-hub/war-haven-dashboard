# Text the leader after a password change

The alert workflow is installed **off**. It runs after a successful password-change
publication and can send one SMS to your private recipient number. Failed password
attempts and ordinary clan data updates do not send a text. Delivery is not instant:
GitHub schedules the workflow and the SMS provider/carrier handles delivery.

## One-time Twilio setup

1. Use a Twilio account and an SMS-capable sender. Follow Twilio's requirements for
   sender registration/verification. Trial accounts can restrict recipients and
   message content; confirm the requirements in your Twilio console. SMS service
   and a sending number may incur charges.
2. In this GitHub repository, open **Settings > Secrets and variables > Actions**.
   Add these **repository secrets**, using your own values:

   | Secret | Value |
   | --- | --- |
   | `TWILIO_ACCOUNT_SID` | Your Twilio account SID |
   | `TWILIO_AUTH_TOKEN` | Your Twilio auth token |
   | `TWILIO_FROM_NUMBER` | Your approved Twilio SMS sender, in `+1...` format |
   | `PASSWORD_ALERT_TO` | Your own phone number, in `+1...` format |

3. Under **Variables**, add `PASSWORD_SMS_ENABLED` with value `true`.
4. Your next successful change from **Settings > Leader settings > Change shared
   password** triggers **Actions > Password change text alert**. Check the workflow
   result and Twilio delivery status. The dashboard does not display or store your
   phone number, and you do not need to send it in chat.

Example text:

> War Haven: shared dashboard password changed at 2026-10-15 23:00 UTC. If this was not you, review your GitHub account.

The SMS never includes the old or new password, publishing token, clan records or
API keys. Your phone number and the alert body are sent to Twilio for delivery.
Turn alerts off by setting `PASSWORD_SMS_ENABLED=false` in GitHub; this is an owner
setting, not a local browser preference. The workflow does not automatically retry
an ambiguous provider submission, to avoid duplicate billed messages. Re-running
an alert job can send another text.

Password rotations published by collector 1.14 using `--setup-website` also
trigger this alert. Older collectors and direct GitHub recovery edits may not
identify a password change; those edits are outside this automatic alert path.

References: [Twilio Messages API](https://www.twilio.com/docs/messaging/api/message-resource),
[Twilio trial accounts](https://www.twilio.com/docs/usage/tutorials/how-to-use-your-free-trial-account).
