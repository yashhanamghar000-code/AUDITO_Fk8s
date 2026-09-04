# Voice Feature — Speak Your Question, Hear the Answer

Two things, both via the browser's own **Web Speech API** — no new
microservice, no new Docker image, no audio files uploaded/stored
anywhere. The browser does the transcription and the reading-aloud
itself; your backend never even knows voice was involved.

1. **Mic button in the chat box** → speak instead of type. You already
   had a disabled placeholder for exactly this in `ChatInput.tsx`
   (`aria-label="Voice (coming soon)"`) — this wires it up for real.
2. **"Listen" button on each answer** → have AUDITO read the response
   aloud. Added next to your existing Copy/Like/Dislike/Regenerate/Share
   row in `MessageBubble.tsx`.

## Why zero backend/infra changes

Both `SpeechRecognition` (speech-to-text) and `SpeechSynthesis`
(text-to-speech) are built into Chrome/Edge. The transcription and audio
playback happen entirely client-side — your `add-ai-backend`,
`add-ai-llm-service`, k8s manifests, and Jenkins pipelines for every other
service are **completely untouched**. Only `add-ai-frontend` changes.

(If you specifically wanted server-side transcription — e.g. Whisper,
for higher accuracy or non-Chrome browser support — that WOULD need a new
`add-ai-audio-service`, a new Dockerfile, a new k8s Deployment, and a new
Jenkins stage. Say the word if you want that version instead; this one is
the zero-new-infra option and is what most chat products actually ship
first.)

## 1. New files — copy these in as-is

```
add-ai-frontend/src/types/speech.d.ts
add-ai-frontend/src/hooks/useSpeechToText.ts
add-ai-frontend/src/hooks/useTextToSpeech.ts
```

No new npm packages — these use browser-native APIs only.

## 2. Edit `src/contexts/ChatContext.tsx` — 3 small patches

**(a) Add the import**, near your other imports at the top:
```ts
import { useTextToSpeech } from "@/hooks/useTextToSpeech";
```

**(b) Add 3 lines to `ChatContextValue`** (right after `reactMessage`):
```ts
  reactMessage: (messageId: string, liked: boolean | null) => void;
  speakingMessageId: string | null;
  toggleSpeak: (messageId: string, text: string) => void;
  stopSpeaking: () => void;
```

**(c) Inside `ChatProvider`, add the hook call** — anywhere near your
other hook calls at the top of the function body:
```ts
  const { speakingId, toggle: toggleSpeak, stop: stopSpeaking } = useTextToSpeech();
```

**(d) Add 3 lines to the `value` object** at the bottom (right after
`reactMessage,`):
```ts
  const value: ChatContextValue = {
    conversations,
    activeId,
    activeConversation,
    isStreaming,
    documents,
    createConversation,
    selectConversation,
    renameConversation,
    deleteConversation,
    sendMessage,
    stopGeneration,
    regenerate,
    reactMessage,
    speakingMessageId: speakingId,
    toggleSpeak,
    stopSpeaking,
    uploadDocument,
    removeDocument,
    toggleDocumentSelection,
  };
```

## 3. Edit `src/components/chat/ChatInput.tsx` — replace the mic button

**Add this import** near the top:
```ts
import { useSpeechToText } from "@/hooks/useSpeechToText";
```

**Add this inside `ChatInput()`**, right after your existing
`const [value, setValue] = useState("");` line:
```ts
  const { isSupported: micSupported, isListening, toggle: toggleMic } = useSpeechToText({
    onFinalResult: (transcript) => {
      setValue((prev) => (prev ? `${prev} ${transcript}` : transcript));
    },
  });
```

**Replace this whole block:**
```tsx
        <Button
          variant="ghost"
          size="icon"
          className="h-9 w-9 shrink-0 rounded-full"
          disabled
          aria-label="Voice (coming soon)"
        >
          <Mic className="h-4 w-4" />
        </Button>
```
**with:**
```tsx
        {micSupported && (
          <Button
            variant="ghost"
            size="icon"
            className={cn(
              "h-9 w-9 shrink-0 rounded-full transition-colors",
              isListening && "bg-red-500/10 text-red-500 hover:bg-red-500/15 hover:text-red-500",
            )}
            onClick={toggleMic}
            aria-label={isListening ? "Stop voice input" : "Start voice input"}
          >
            {isListening ? (
              <motion.div
                animate={{ scale: [1, 1.15, 1] }}
                transition={{ duration: 1, repeat: Infinity, ease: "easeInOut" }}
              >
                <Mic className="h-4 w-4" />
              </motion.div>
            ) : (
              <Mic className="h-4 w-4" />
            )}
          </Button>
        )}
```
(the button now hides itself entirely on Firefox/Safari, where
`SpeechRecognition` isn't implemented, instead of sitting there disabled)

**Update the placeholder text** so it's clear voice works, purely
cosmetic — find:
```tsx
          placeholder="Ask AUDITO AI anything..."
```
and optionally change to:
```tsx
          placeholder={isListening ? "Listening…" : "Ask AUDITO AI anything..."}
```

## 4. Edit `src/components/chat/MessageBubble.tsx` — add the Listen button

**Add these to your lucide-react import line** (find the `import { Copy, Check, ThumbsUp, ThumbsDown, RefreshCw, Share2 } from "lucide-react";` line):
```ts
import {
  Copy,
  Check,
  ThumbsUp,
  ThumbsDown,
  RefreshCw,
  Share2,
  Volume2,
  VolumeX,
} from "lucide-react";
```

**Pull the new context values** — find where you already destructure
`useChat()` in this file (likely near the top of the component function,
something like `const { regenerate, reactMessage, ... } = useChat();`)
and add the two new fields:
```ts
  const { regenerate, reactMessage, speakingMessageId, toggleSpeak } = useChat();
```
(merge with whatever's already being destructured there — don't
duplicate the `useChat()` call)

**Add the Listen button** to the existing action row — find:
```tsx
            <IconAction
              label="Share"
              onClick={() => {
                navigator.clipboard.writeText(message.content);
                toast.success("Response copied to clipboard");
              }}
            >
              <Share2 className="h-3.5 w-3.5" />
            </IconAction>
```
and add this right after it (still inside the same `<div>`):
```tsx
            <IconAction
              label={speakingMessageId === message.id ? "Stop" : "Listen"}
              onClick={() => toggleSpeak(message.id, message.content)}
              active={speakingMessageId === message.id}
            >
              {speakingMessageId === message.id ? (
                <VolumeX className="h-3.5 w-3.5" />
              ) : (
                <Volume2 className="h-3.5 w-3.5" />
              )}
            </IconAction>
```

That's the whole feature. Restart your dev server (`npm run dev` /
`bun dev`) and test: click the mic, say something, watch it appear in the
box; click Listen on any answer, hear it read back; click again (now
showing the mute icon) to stop early.

---

## Git → Docker → K8s flow for this change

Since I can see your `k8s/frontend.yaml`, here's the exact flow matching
your actual setup (`image: yashhanamghar/audito-frontend:latest`,
`imagePullPolicy: Never` — this tells me you're running a **local**
cluster, minikube or kind, that loads images directly rather than pulling
from a registry):

### 1. Commit and push — only the `add-ai-frontend` repo changes
```bash
cd add-ai-frontend
git checkout -b feature/voice-input-output
git add src/types/speech.d.ts src/hooks/useSpeechToText.ts src/hooks/useTextToSpeech.ts \
        src/contexts/ChatContext.tsx src/components/chat/ChatInput.tsx src/components/chat/MessageBubble.tsx
git commit -m "Add voice input (speech-to-text) and answer read-aloud (text-to-speech)"
git push origin feature/voice-input-output
```
Open a PR / merge to `main` per however your workflow already works —
none of your other 13 repos need a commit for this change.

### 2. Build the Docker image
```bash
cd add-ai-frontend
docker build -t yashhanamghar/audito-frontend:latest .
```

### 3. Load it into your local cluster
Whichever one you're running:
```bash
# minikube:
minikube image load yashhanamghar/audito-frontend:latest

# kind:
kind load docker-image yashhanamghar/audito-frontend:latest
```

### 4. Roll the deployment
Because the tag is `:latest` and `imagePullPolicy: Never`, Kubernetes
won't automatically notice the image changed — force a rollout:
```bash
kubectl rollout restart deployment/frontend -n audito
kubectl rollout status deployment/frontend -n audito
```

### 5. Jenkins — I don't see a `Jenkinsfile` in the zip you sent

I looked for one in `add-ai-frontend/` and the repo root and didn't find
it, so I can't give you an exact patch for your real pipeline. If you
already have Jenkinsfiles for your other services (backend, worker,
etc.), the frontend one should mirror that same shape — something like:

```groovy
pipeline {
    agent any
    stages {
        stage('Checkout') {
            steps { git branch: 'main', url: 'https://github.com/<you>/add-ai-frontend.git' }
        }
        stage('Build Docker Image') {
            steps {
                sh 'docker build -t yashhanamghar/audito-frontend:latest .'
            }
        }
        stage('Load into Cluster') {
            steps {
                // swap for `kind load docker-image ...` if that's what you use
                sh 'minikube image load yashhanamghar/audito-frontend:latest'
            }
        }
        stage('Deploy') {
            steps {
                sh 'kubectl rollout restart deployment/frontend -n audito'
                sh 'kubectl rollout status deployment/frontend -n audito'
            }
        }
    }
}
```

If you paste me your actual Jenkinsfile from one of the other services
(backend or worker, say), I'll adapt this to match its exact style/stage
names instead of guessing.
