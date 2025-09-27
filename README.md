# ArchFairFight

A modular Telegram bot system for managing voice chat challenges between users. Users can challenge each other to epic voice chat battles with automated monitoring, recording, and AI-powered winner determination.

## Features

🥊 **Challenge System**
- Challenge friends to voice chat fights using `/challenge @username`
- Accept/Decline buttons for seamless interaction
- Multiple fight types: Timing fights and Volume fights

⚔️ **Fight Types**
- **Timing Fight**: Stay in voice chat as long as possible - last person standing wins
- **Volume Fight**: Most active speaker wins based on participation and volume

🤖 **Automated Monitoring**
- Userbots automatically join voice chats to monitor fights
- Real-time participant tracking and metrics collection
- Automatic recording of all fights (audio/video)
- 30-second join timeout for participants

🏆 **Winner Determination**
- AI-powered winner detection based on activity metrics
- Volume-based analysis for fair judging
- Automatic statistics updates and leaderboards

📊 **Statistics & Leaderboards**
- Personal fight statistics with win/loss records
- Global leaderboards showing top fighters
- Fight history and performance trends
- Achievement system for active participants

🎥 **Recording System**
- Automatic recording of all fights
- Multiple formats supported (audio/video)
- Portrait/landscape video modes
- Recording metadata stored in database

🧠 **AI Features** (Optional)
- Automated winner detection based on voice activity
- Fight quality analysis and insights
- Performance predictions and statistics
- Auto-moderation capabilities

## Architecture

The system is built with a **modular architecture** for easy extension:

```
archfairfight/
├── bot/           # Pyrogram bot with command handlers
├── userbot/       # PyTgCalls userbot controllers  
├── database/      # MongoDB operations and models
├── challenge/     # Challenge management and state machine
├── recording/     # Recording management system
├── ai/           # AI features for winner detection
├── utils/        # Logging and utilities
└── config.py     # Configuration management
```

## Requirements

- Python 3.8+
- MongoDB database
- Telegram Bot Token and API credentials
- One or more Telegram user accounts for userbots

## Installation

1. Clone the repository:
```bash
git clone https://github.com/ChiranjibKoch/ArchFairFight.git
cd ArchFairFight
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create configuration file:
```bash
cp config/config.example.env .env
```

4. Edit `.env` with your credentials:
```env
BOT_TOKEN=your_bot_token_here
API_ID=your_api_id
API_HASH=your_api_hash
MONGODB_URL=mongodb://localhost:27017
USERBOT_SESSIONS=sessions/userbot1.session,sessions/userbot2.session
```

5. Setup userbot sessions:
```bash
# Login to your userbot accounts to generate session files
python -c "from pyrogram import Client; Client('sessions/userbot1', api_id=YOUR_API_ID, api_hash='YOUR_API_HASH').start()"
```

## Usage

### Starting the Bot

```bash
# Run directly
python -m archfairfight.main

# Or using the installed command
archfairfight
```

### Bot Commands

- `/start` - Register and get welcome message
- `/challenge @username` - Challenge someone to a fight
- `/stats` - View your fight statistics  
- `/leaderboard` - See top 10 fighters
- `/help` - Get help and instructions

### Fight Flow

1. User sends `/challenge @opponent`
2. Bot sends challenge message with Accept/Deny buttons to opponent
3. If accepted, opponent chooses fight type (Timing/Volume)
4. Both participants have 30 seconds to join the voice chat
5. Userbots monitor the fight and collect metrics
6. Fight ends automatically or after maximum duration
7. Winner determined by AI analysis of metrics
8. Results saved to database and statistics updated

## Configuration

Key configuration options in `.env`:

```env
# Challenge Settings
CHALLENGE_TIMEOUT=30              # Seconds to join after accepting
MAX_FIGHT_DURATION=300           # Maximum fight duration (5 minutes)
MONITORING_INTERVAL=10           # VC monitoring interval

# AI Features  
ENABLE_AI_WINNER_DETECTION=true
ENABLE_AUTO_MODERATION=false
VOLUME_THRESHOLD=0.5

# Recording
RECORDINGS_PATH=./recordings
MAX_RECORDING_SIZE=500           # MB

# Database
DATABASE_NAME=archfairfight
```

## Database Schema

MongoDB collections:

- **users**: User profiles and statistics
- **challenges**: Active and completed challenges  
- **fights**: Fight results and metrics
- **recordings**: Recording metadata and file info

## API Functions Used

The bot utilizes Telegram's raw API functions for advanced VC control:

- `phone.GetGroupCall` - Fetch group call info and participants
- `phone.EditGroupCallParticipant` - Mute/unmute, adjust volume
- `phone.EditGroupCallTitle` - Change VC title
- `phone.ToggleGroupCallRecord` - Start/stop recording
- `phone.GetGroupCallJoinAs` - Get available join-as peers

## Development

### Project Structure

```
archfairfight/
├── __init__.py
├── main.py              # Application entry point
├── config.py            # Configuration management
├── bot/                 # Bot command handlers
│   ├── client.py        # Pyrogram bot client
│   ├── handlers.py      # Command and callback handlers
│   └── utils.py         # Bot utilities
├── userbot/             # Userbot VC control
│   ├── controller.py    # Single userbot controller
│   └── manager.py       # Multi-userbot manager
├── database/            # Database layer
│   ├── connection.py    # MongoDB connection
│   ├── models.py        # Pydantic models
│   └── operations.py    # CRUD operations
├── challenge/           # Challenge management
│   ├── manager.py       # Challenge lifecycle
│   └── state_machine.py # State transitions
├── recording/           # Recording system
│   └── manager.py       # Recording operations
├── ai/                  # AI features
│   ├── winner_detector.py # Winner determination
│   └── stats_analyzer.py  # Statistics analysis
└── utils/
    └── logging.py       # Structured logging
```

### Adding New Features

The modular architecture makes it easy to extend:

1. **New Fight Types**: Add to `FightType` enum and implement logic in `ChallengeManager`
2. **AI Features**: Extend `WinnerDetector` or `StatsAnalyzer` classes
3. **Bot Commands**: Add handlers in `bot/handlers.py`
4. **Database Models**: Add new models in `database/models.py`

### Testing

```bash
# Install development dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and questions:
- Open an issue on GitHub
- Check the documentation in the `docs/` folder
- Review the example configuration files

---

**Made with ❤️ for the Telegram fighting community!** ⚔️