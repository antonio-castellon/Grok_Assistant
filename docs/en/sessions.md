[← README.md](../../README.md)

# Sessions and agents

Think of a session as the conversation's local notebook. It stays on this computer. The shared session resets after 24 hours, while a named session remains until you delete it. These local sessions are separate from your Grok account.

An agent belongs to your Grok account and is opened explicitly with `comando abrir agente …`. The Agent menu lists the files on this PC (`~/.grok/agents`) and the agents the signed-in account already publishes. It can remember things such as dates, places, and lists, and it can look information up when needed. Because that memory belongs to the account, the same agent is available on another computer where you are signed in. Creating one saves a file on this PC and requires the administrator password.

Saying goodbye (`gracias`, `vale`, `adiós`) ends the current conversation, but it does not delete or close the session. Closing a session returns you to the shared session. `comando cerrar agente` leaves the current agent and returns to the regular assistant; the agent itself is not deleted. Its account-based memory does not depend on this laptop staying on, and you always enter an agent explicitly.
