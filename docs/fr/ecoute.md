[← README.FR.md](../../README.FR.md)

# L'espagnol d'abord, parce qu'il a été développé et essayé d'abord en espagnol

À la maison, nous parlons espagnol, c'est donc la langue par laquelle l'assistant commence. Les réponses restent volontairement courtes : dans une pièce bruyante, une réponse concise est bien plus facile à suivre qu'un long monologue.

La partie la plus délicate est le STT, c'est-à-dire la conversion de la parole en texte. Tout le reste dépend de la qualité de cette première transcription. L'audio est traité localement et ne quitte jamais l'ordinateur. Le moteur STT s'en charge, mais il peut se tromper sur un mot : « hola » peut devenir « ola », ou un nom anglais peut être interprété comme de l'espagnol. Si la transcription est incorrecte, une commande peut ne plus être reconnue et une question peut ne jamais parvenir à Grok.

Le moteur STT en flux s'occupe de l'écoute en espagnol à la maison. Whisper base, un autre moteur STT, gère mieux les noms anglais et reconnaît également le français, l'allemand et l'anglais. La langue se change depuis le menu **Langue**, et Voice Market télécharge le modèle vocal nécessaire à la demande.
