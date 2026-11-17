# 0015 A password change revokes harness tokens

Date: 2026-11-17. Status: accepted by the author ("si hace lo recomendado"), after the Deepsec scan of that day.

- **Change:** changing a password in **Account** ends the other panel sessions and revokes every harness token of that account. Before, the tokens kept working.
- **Why:** harness tokens never expire, and whoever knew the old password could have created one. A person who changes a password because the account may be compromised expects everything to be cut. A reset link already behaved this way.
- **Cost:** after a routine change the person creates new tokens in **Connect** and reconnects each harness. The panel says so before and after the change.
- **Alternative not taken:** keep the tokens and show how many remain active, as GitHub does with personal tokens.
- **Unchanged:** the session that made the change stays signed in.
