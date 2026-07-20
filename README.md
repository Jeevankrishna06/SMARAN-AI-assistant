# 🐼 SMARAN – Voice-First Desktop AI Assistant

> *"Smaran" is a Sanskrit word meaning **Remembrance** or **Memory**.*

Smaran is a voice-first desktop AI assistant built to automate everyday computer tasks, provide intelligent assistance, and create personalized productivity environments through simple voice commands.

Unlike traditional chatbot-style assistants, Smaran combines **desktop automation**, **AI-powered reasoning**, **workflow modes**, and **computer vision** into a unified desktop ecosystem.

---

# 🎥 Demo



---

# ✨ Features

## 🎙️ Voice Assistant

* Wake phrase activation
* Natural voice interaction
* Local text-to-speech
* Intelligent command execution

---

## 💻 Desktop Automation

Control your computer using voice commands.

Examples include:

* Open applications
* Open browsers
* Launch AI tools
* Search the web
* Play music
* Play YouTube videos
* Open and type into Notepad
* Perform calculations
* Weather updates
* Random number generation

---

## 🤖 Intelligence Layer

Smaran contains an optional Intelligence Mode that routes user queries to specialized AI agents.

Current supported agents include:

* 🌦 Weather Agent
* 📖 Dictionary Agent
* 📚 Wikipedia Agent
* 📰 News Agent
* 🧠 Gemini Reasoning Agent

A confidence-based routing system determines which agent is best suited for each request before generating a response.

---

## 🎯 Workflow Modes

Smaran can automatically prepare your desktop for different activities.

### 📚 Study Mode

* Opens study resources
* Plays study music
* Launches Gemini
* Opens File Explorer
* Creates a distraction-free workspace

### 👨‍💻 Developer Mode

* Opens VS Code
* Opens Terminal
* Launches Claude & Gemini
* Starts coding music
* Prepares a development workspace

### 🎮 Fun Mode

* Opens entertainment applications
* Plays music
* Sets break timers

### 🧠 Deep Mode

* Opens Notepad
* Opens browser
* Creates a writing and reflection environment

---

## ✋ Vision Mode *(Experimental)*

Vision Mode introduces computer vision capabilities for desktop interaction.

Current capabilities include:

* Hand tracking
* Gesture recognition
* Cursor control
* Mouse interaction

---

# 🏗️ Architecture

```text
User Voice
      │
      ▼
Speech Recognition
      │
      ▼
Command Processing
      │
      ├───────────────► Desktop Automation
      │
      ├───────────────► Intelligence Router
      │                     │
      │                     ├── Weather
      │                     ├── Dictionary
      │                     ├── Wikipedia
      │                     ├── News
      │                     └── Gemini
      │
      ▼
Text-to-Speech
```

---

# 🛠️ Tech Stack

### Programming Language

* Python

### AI & APIs

* Groq
* Google Gemini
* OpenWeather
* Wikipedia API
* Free Dictionary API
* GNews API

### Automation

* PyAutoGUI
* PyWin32
* Webbrowser
* Subprocess

### Computer Vision

* OpenCV
* MediaPipe

### Audio

* SpeechRecognition
* PyAudio
* pyttsx3

### Core Libraries

* NumPy
* Requests
* Pillow

---

# 📂 Project Structure

```text
SMARAN/
│
├── assets/
├── automation/
├── intelligence/
├── vision/
├── gui/
├── utilities/
├── main.py
└── README.md
```

*(Folder names may vary as the project evolves.)*

---

# 🚀 Getting Started

Clone the repository:

```bash
git clone https://github.com/Jeevankrishna06/SMARAN-AI-assistant.git
```

Navigate to the project:

```bash
cd SMARAN-AI-assistant
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the project:

```bash
python main.py
```

---

# 📈 Roadmap

### ✅ Phase I

* Voice assistant
* Desktop automation
* Workflow modes
* GUI
* Voice interaction

### 🚧 Phase II

* Multi-agent intelligence
* Intelligent routing
* API integrations

### 🔬 Phase III

* Enhanced computer vision
* Additional workflow modes
* Expanded automation capabilities

---

# 💡 Why I Built Smaran

I wanted to explore how modern AI systems can go beyond answering questions and instead become practical desktop companions.

Smaran started as a personal learning project and has gradually evolved into a platform for experimenting with:

* AI agents
* Desktop automation
* Human-computer interaction
* Workflow optimization
* Computer vision

As a first-year AI & Machine Learning student, this project has been one of my primary ways of learning by building.

---

# ⚠️ Disclaimer

Smaran is an actively evolving project. New features, improvements, and architectural changes will continue to be added over time.

---

# 📬 Feedback

If you have suggestions, ideas, or feedback, feel free to open an issue or connect with me on LinkedIn.

Contributions, discussions, and constructive feedback are always welcome.

---

## ⭐ If you found this project interesting, consider giving it a star!
