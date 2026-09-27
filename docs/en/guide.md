[← README.md](../../README.md)

# How to use it

Short steps to open the program, set it up, and talk to it. Each long chapter stays in its own page.

## Open

1. Double-click `GrokAssistant.exe`. There is no installer, and Python is not required.
2. If a Grok Build window appears, click **Install Grok Build**, then **Sign in** in the browser, then **Check**. **Continue** opens the assistant even when the cloud is not ready. Local orders still work. There is no key to paste.
3. The window opens. The top right says **WAITING**. The Grok icon stays in the tray.
4. Left-click the icon to show the window. Right-click it to open the menu.
5. Closing the window hides it. **Quit** closes the program.

## Set up

Do this once, in this order.

1. **Language.** Pick Español, Français, Deutsch, or English. Menus and answers switch to that language.
2. **Listening engine (STT).** This is the program that turns speech into text. Pick one in the menu. If it is missing, open **Voice market**, tab **Listening engine (STT)**, and download it. It can be chosen when the download reaches 100%.
3. **Voice.** Pick a voice in the same language. **Voice market**, tab **Voices**, has more. Only voices for the active language are listed.
4. **Print.** **Admin → Prints.** Open your name, or **New print…**. Choose the same STT engine you will use. Say the twelve phrases. If a take does not catch the microphone, it asks you to repeat it. The menu shows a number when that engine has a print, or **no print** when it does not. A print from one engine does not work on another.
5. **Password.** Only if you will create agents. **Admin → Password…**. Type it twice. The program stores a hash, not the password itself.
6. **Start with Windows** stays off until you turn it on under **Admin**.

## Talk

1. Say the wake name. At the start it is `hola grok`. The top right changes to **IN CONVERSATION**.
2. Then talk. A question goes to Grok. An order can start with `command`.
3. `thanks`, `okay`, or `goodbye` returns to **WAITING**. The session is not deleted.
4. For a song, say the title. The first time, the player downloads.
5. The window log shows what was heard. Under it, `LLM:` is what the local model decided and `Grok:` is the answer.

More detail: [Voice prints and listeners](prints.md) · [What you can say](saying.md) · [Run the executable](run.md)
