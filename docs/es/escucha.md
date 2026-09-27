[← README.ES.md](../../README.ES.md)

# Español primero, porque inicialmente se desarrolló y se probó en español

En casa hablamos español, así que el asistente empieza por ahí. Las respuestas son deliberadamente breves: cuando hay ruido alrededor, es mucho más fácil seguir una respuesta corta que un discurso largo.

La parte más delicada es el STT, es decir, convertir la voz en texto. Todo lo demás depende de que esas primeras palabras se entiendan bien. El audio se procesa localmente y no sale del ordenador. El motor de STT hace la transcripción, pero puede confundir palabras: «hola» puede convertirse en «ola», o un nombre inglés puede interpretarse como si fuera español. Si la transcripción falla, una orden puede dejar de coincidir y una pregunta puede no llegar nunca a Grok.

El motor de STT en streaming se ocupa del español en casa. Whisper base, otro motor de STT, ayuda a conservar mejor los nombres en inglés y también reconoce francés, alemán e inglés. El idioma se puede cambiar desde el menú **Idioma**, y Voice Market descarga el modelo de voz necesario cuando hace falta.
