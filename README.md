# AI News Analyst

A modern web interface for AI-powered news analysis, featuring curated AI news articles, intelligent summaries, and interactive chat capabilities.

## Features

- **📰 News Dashboard**: Browse the latest AI news articles with summaries and direct links
- **🤖 AI Summary**: Generate intelligent weekly summaries using advanced language models
- **💬 Interactive Chat**: Ask questions about news articles and get AI-powered insights
- **🎨 Modern UI**: Beautiful, responsive design with smooth animations and intuitive navigation

## Project Structure

```
ai_news/
├── agents/                 # AI processing modules
│   ├── chat_bot/          # Chat interface with news analyst
│   ├── doc_loader/        # News loading and processing
│   └── reporter/          # Weekly summary generation
├── data/                  # News data storage
├── static/                # Web assets (CSS, JS)
├── templates/             # HTML templates
├── app.py                 # Flask web application
└── requirements.txt       # Python dependencies
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

Create a `.env` file in the project root:

```bash
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Run the Web Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Usage

### News Section
- View the latest AI news articles
- Read summaries and access full articles
- Use "Ask About This" buttons to get more information

### Summary Section
- Automatically generates AI-powered weekly summaries
- Click "Generate New Summary" to create fresh insights
- Summaries are based on the current week's articles

### Chat Section
- Ask questions about news articles, trends, or specific topics
- Get AI-powered analysis and insights
- Use suggestion buttons for quick questions
- Maintains conversation history during your session

## API Endpoints

- `GET /` - Main application interface
- `GET /api/summary` - Generate weekly AI summary
- `POST /api/chat` - Send chat message and get response
- `GET /api/news` - Retrieve news data

## Technologies Used

- **Backend**: Flask, Python
- **AI/ML**: LangChain, OpenAI GPT models
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Styling**: Modern CSS with gradients, animations, and responsive design
- **Icons**: Font Awesome
- **Fonts**: Inter (Google Fonts)

## Development

### Running in Development Mode

```bash
export FLASK_ENV=development
python app.py
```

### Customizing the Interface

- Modify `templates/index.html` for layout changes
- Update `static/css/style.css` for styling modifications
- Edit `static/js/app.js` for JavaScript functionality

## Data Sources

The application currently uses MIT AI news data stored in JSON format. The system is designed to be easily extensible for additional news sources.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Support

For questions or issues, please open an issue in the repository or contact the development team.
# ai_news
