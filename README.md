# 🌟 AI Journaling Assistant

Your personal companion for reflection, growth, and self-discovery powered by Llama 3 via Ollama.

## Features

- **Interactive Chat Interface**: Both CLI and web-based UI options
- **Mood Tracking**: Set and track your current emotional state
- **Goal Management**: Add, track, and manage personal goals
- **Conversation History**: Save and revisit past journaling sessions
- **Smart Summaries**: Auto-generate conversation summaries
- **Data Export**: Export your journal entries in markdown format
- **Reflection Prompts**: Built-in prompts for daily reflection and gratitude practice

## Prerequisites

- **Python 3.8+**
- **Pixi** package manager (recommended) - [Install Pixi](https://pixi.sh/latest/)
- **Ollama** with Llama 3 model - [Install Ollama](https://ollama.ai/)

## Installation

### 1. Install Ollama and Download Llama 3

```bash
# Install Ollama (if not already installed)
curl -fsSL https://ollama.ai/install.sh | sh

# Download and run Llama 3 model
ollama run llama3:latest
```

### 2. Clone and Setup the Project

```bash
# Clone the repository
git clone <your-repo-url>
cd journaling

# Install dependencies using Pixi (recommended)
pixi install
```

### Alternative: Manual Python Setup

If you prefer not to use Pixi:

```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install pydantic-ai httpx ollama streamlit nest-asyncio jinja2
```

## Usage

### Option 1: Web Interface (Recommended)

Launch the Streamlit web application:

```bash
# Using Pixi
pixi run journal-ui

# Or manually
streamlit run streamlit_app.py --server.headless false --theme.base light
```

The web interface provides:
- Beautiful chat interface
- Sidebar with mood tracking and conversation history
- Quick action buttons for common journaling prompts
- Settings panel for profile and goal management
- Export functionality

### Option 2: Command Line Interface

#### Interactive CLI Mode

```bash
# Using Pixi
pixi run journal-cli

# Or manually
python interactive_journal.py
```

#### Direct Chat (Single Query)

```bash
# Using Pixi
pixi run python src/journaling_assistant/chat.py "How can I improve my morning routine?"

# Or manually
python src/journaling_assistant/chat.py "How can I improve my morning routine?"
```

## Project Structure

```
journaling/
├── src/journaling_assistant/    # Core application modules
│   ├── agent.py                 # Main journaling assistant agent
│   ├── chat.py                  # Simple chat interface
│   ├── database.py              # SQLite database management
│   ├── ollama_model.py          # Ollama integration
│   ├── summarizer.py            # Conversation summarization
│   ├── sync_agent.py            # Synchronous agent wrapper
│   └── template_manager.py      # Jinja2 template management
├── templates/                   # Prompt templates
│   ├── context_aware_responses.j2
│   ├── conversation_summary.j2
│   ├── reflection_prompts.j2
│   └── system_prompt.j2
├── streamlit_app.py             # Web UI application
├── interactive_journal.py       # CLI application
├── run_journal_agent.py         # Alternative runner
├── run_streamlit.py            # Streamlit runner
├── journaling.db               # SQLite database (created on first run)
├── pixi.toml                   # Pixi configuration
└── README.md                   # This file
```

## Configuration

The application uses SQLite for data storage and creates a `journaling.db` file automatically on first run. All conversations, messages, and user data are stored locally.

### Templates

The application uses Jinja2 templates located in the `templates/` directory:
- `system_prompt.j2` - Main system prompt for the AI assistant
- `reflection_prompts.j2` - Daily reflection prompts
- `conversation_summary.j2` - Template for generating conversation summaries
- `context_aware_responses.j2` - Context-aware response templates

## Troubleshooting

### Common Issues

1. **"Model not found" error**
   ```bash
   # Make sure Llama 3 is downloaded
   ollama run llama3:latest
   ```

2. **"Connection refused" error**
   ```bash
   # Start Ollama service
   ollama serve
   ```

3. **Import errors**
   ```bash
   # Make sure you're in the right directory and dependencies are installed
   pixi install  # or pip install -r requirements.txt
   ```

4. **Streamlit issues**
   ```bash
   # Clear Streamlit cache
   streamlit cache clear
   ```

## Data Export

Your journal data can be exported in markdown format:
- **Current Session**: Export the current conversation
- **All Conversations**: Export your complete journal history

Access export options through the web interface Settings panel.

## Development

### Running Tests

```bash
# Add test commands here when implemented
pixi run test  # or python -m pytest
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

[Add your license information here]

## Support

For issues and questions:
- Check the troubleshooting section above
- Review Ollama documentation
- Open an issue in the repository