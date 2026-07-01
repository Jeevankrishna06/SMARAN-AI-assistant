# SMARAN - AI Desktop Assistant

## Overview

Smaran is a voice-first desktop assistant designed to combine desktop automation, intelligent query handling, workflow management, and computer vision into a single system.

The name **Smaran** comes from Sanskrit and means *remembrance* or *memory*.

Smaran can be activated either through voice commands or clap detection and responds using speech, automation, intelligence agents, and vision-based controls.

---

# Wake System

Smaran supports two activation methods:

### Voice Wake

* Wake up Smaran
* Wake up

### Clap Wake

* Detects hand claps using audio analysis.
* Wakes the assistant without requiring speech.

Once activated, Smaran appears as a Chibi Panda assistant with animated expressions and voice interaction.

---

# Phase I - Automation Layer

The Automation Layer focuses on desktop control and productivity automation.

### Assistant Functions

* Greetings and introductions
* Briefings
* Quotes
* Random number generation
* Weather reports

### Desktop Automation

* Open applications
* Open websites
* Browser automation
* Search automation
* Music playback
* Video playback
* Calculations
* Notepad automation

### Supported Browsers

* Chrome
* Brave
* Opera GX
* Microsoft Edge

### Supported AI Platforms

* ChatGPT
* Gemini
* Claude
* Grok
* Perplexity

### Quiet Mode

Suspends microphone listening until manually resumed.

---

# Phase II - Intelligence Layer

The Intelligence Layer introduces agent-based intelligence.

Activation:

```text
Activate Intelligence Mode
```

Smaran uses a confidence-based routing system that determines which agent should handle a query.

### Routing Flow

```text
User Query
↓
Weighted Scoring
↓
Confidence Evaluation
↓
Agent Selection
↓
Response Generation
↓
Voice Output
```

### Available Agents

#### Weather Agent

Provides:

* Weather summaries
* Temperature
* Rain probability
* Sunrise and sunset
* Humidity
* Wind speed

#### Dictionary Agent

Provides:

* Definitions
* Meanings
* Pronunciations

#### Wikipedia Agent

Provides:

* Research
* Historical information
* General knowledge

#### News Agent

Provides:

* Current news
* Topic-based news
* Recent events

#### Gemini Agent

Provides:

* Explanations
* Comparisons
* Decision support
* General reasoning
* Fallback intelligence

---

# System Modes

Smaran includes workflow-focused environments.

### Study Mode

Creates a study environment by opening:

* Clock
* Study Music
* Gemini
* WhatsApp
* File Explorer
* Intelligence Mode

### Developer Mode

Creates a coding environment by opening:

* VS Code
* Terminal
* Claude
* Gemini
* Coding Music
* Intelligence Mode

### Fun Mode

Creates an entertainment environment by opening:

* Opera GX
* YouTube
* YouTube Music
* Clock

### Deep Mode

Creates a reflection environment by opening:

* Chrome
* YouTube
* Notepad
* Clock

---

# Vision Mode

Vision Mode enables touchless desktop control through hand gestures.

### Features

* Hand Tracking
* Cursor Control
* Gesture Recognition
* Mouse Interaction

### Supported Gestures

#### Single Hand

* Cursor Movement
* Left Click
* Right Click
* Drag
* Select

#### Two Hands

* Open Selected Item
* Close Active Window

#### System Control

* Exit Vision Mode

---

# Technology Stack

### Language

* Python

### APIs

* Groq API
* Google Gemini API
* OpenWeatherMap API
* Wikipedia API
* GNews API
* Free Dictionary API

### Computer Vision

* MediaPipe
* OpenCV

### Automation

* PyAutoGUI
* PyWin32

### Speech Processing

* SpeechRecognition
* PyAudio
* pyttsx3

---

# Design Philosophy

Smaran follows a Free-First Development Philosophy.

* Use free APIs whenever possible.
* Use specialized agents instead of a single model.
* Separate automation from intelligence.
* Focus on workflow enhancement rather than chatbot-style interaction.

The goal of Smaran is not to be a chatbot.

The goal is to act as a voice-first desktop assistant that combines automation, intelligence, and computer vision into a unified ecosystem.