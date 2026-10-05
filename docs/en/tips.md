[← README.md](../../README.md)

# Tips

## The print keeps people apart

The voice print is there so two people in the same room are not mixed into one conversation. Once it is ready, the microphone follows a saved voice. Someone else speaking is left out before the local model, and before an order. **Listen → Turn test on** shows the words and does nothing with them. The same row becomes **Turn test off**. `salir` leaves as well. The corner says TEST.

## The microphone is part of the print

A quiet or muddy microphone makes both the words and the print less sure. The print is the voice as that microphone heard it. The same person on another microphone can fall short of the match, even when the words on screen are right. Record the print again on the microphone you will use.

**Settings → Microphone** switches the microphone. If that one already has a print, that print is the one used. A microphone with no print of its own keeps the earlier print until you record it there. **Default** is the Windows microphone.

## How a phrase ends

A phrase closes 1.2 seconds after the last new word, once there has been at least 0.4 seconds of voice. A shorter noise does not count. With **Hello first**, a bare greeting waits 2 seconds while the chat is still closed, so the question can follow. The minutes on Simple close the chat. They do not close the phrase. The fastest way is the wake name and the question in one breath: «Hello grok, what time is it?».

## While it answers

The microphone stays open while the assistant speaks. The print drops the assistant's own voice. **Pause listening** and a print recording still close the microphone. While a song plays, only a saved voice is followed. If another program already holds the microphone, this one cannot open it. Pick another microphone, or close the program that has it.

## What the debug lines mean

`LLM: comando o accion no detectada` means the small local model did not see a command. The listening engine did hear the phrase. With the chat closed, that phrase stays on the computer. Open the chat first, or put the question in the same breath as the name. **Clear log** empties the debug window. Later phrases show again. **Save a trace** packs a zip of this run. The audio of the house stays on this computer. Grok receives the text of a question or an order.
