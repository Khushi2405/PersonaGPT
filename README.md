# Khushi Gandhi's AI Career Assistant 🤖

An intelligent conversational AI bot that represents my professional profile, built using advanced RAG (Retrieval-Augmented Generation) techniques and modern web technologies. The bot answers questions about my career, skills, experience, and personality while automatically collecting interested recruiters' contact information.

## 🌟 Features

### 🧠 Intelligent Conversation
- **RAG-powered responses** using semantic search and embeddings
- **Intent classification** to understand user queries and route to relevant information sections
- **Behavioral question handling** with STAR format responses (Situation, Task, Action, Result)
- **Natural language processing** using Google's Gemini 2.0 Flash model
- **Context-aware responses** that synthesize information rather than copy-pasting
- **Smart contact collection** through natural conversation flow
- **Automatic email follow-ups** sent via Supabase Edge Functions
- **Clean Gradio interface** with example questions to guide users

## 🛠️ Technology Stack

### Backend & AI
- **Python 3.8+** - Main application language
- **Sentence Transformers** - Text embeddings using `all-MiniLM-L6-v2`
- **OpenAI API** - LLM integration via Google Gemini 2.0 Flash
- **scikit-learn** - Cosine similarity for semantic search
- **NumPy** - Numerical operations for embeddings

### Frontend & Interface
- **Gradio** - Interactive chat interface
- **HTML/CSS** - Custom styling and theming

### Database & Backend Services
- **Supabase** - PostgreSQL database with real-time capabilities
- **Supabase Edge Functions** - Serverless functions for email automation
- **TypeScript/Deno** - Edge function runtime

## 📁 Project Structure

```
career-bot/
├── me/
│   └── details.txt                 # Personal information and career data
├── supabase/
│   └── functions/
│       └── send-email/
│           └── index.ts           # Edge function for email automation
├── create_embeddings.py          # Script to generate embeddings from personal data
├── app.py                        # Main chat application
├── embeddings_by_section.pkl     # Generated embeddings file
├── .env                          # Environment variables (not in repo)
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## 🚀 Quick Start Guide

### Prerequisites

Before you begin, ensure you have:
- **Python 3.8 or higher**
- **Supabase account** (free tier works)
- **Google AI Studio account** for Gemini API and create a new API Key
- **Gmail account** with App Password enabled

### Step 1: Clone and Setup

```bash
# Clone the repository
git clone https://github.com/Khushi2405/PersonaGPT.git
cd PersonaGPT

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Create Your Personal Data File

Create a `me/details.txt` file with your information using similar format

### Step 3: Set Up Supabase Database

1. **Create a new Supabase project** at [supabase.com](https://supabase.com)

2. **Run this SQL in the Supabase SQL editor:**

```sql
-- Create the emails_sent table
CREATE TABLE IF NOT EXISTS emails_sent (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  email VARCHAR(255) NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable Row Level Security (recommended)
ALTER TABLE emails_sent ENABLE ROW LEVEL SECURITY;
```

3. **Create a webhook** in Supabase Dashboard:
   - Go to Database → Webhooks
   - Create new webhook for `emails_sent` table
   - Select "Insert" event
   - Set URL to your Edge Function endpoint


### Step 4: Configure Environment Variables

Create a `.env` file in the project root:

```env
# Google AI API
GOOGLE_API_KEY=your_gemini_api_key_here

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

```

### Step 5: Gmail App Password Setup

1. **Enable 2-factor authentication** on your Gmail account
2. **Go to your Google Account settings**
3. **Navigate to Security → 2-Step Verification → App passwords**
4. **Generate an app password** for "Mail"
5. **Use this 16-character password** later for supabase setup

### Step 6: Deploy Supabase Edge Function

You can deploy the edge function using either the CLI or the Supabase Dashboard UI.

#### Option A: Deploy via Supabase CLI (Recommended)

1. **Install Supabase CLI:**
```bash
npm install -g supabase
```

2. **Login and link your project:**
```bash
supabase login
supabase link --project-ref your-project-ref
```

3. **Initialize functions (if needed):**
```bash
supabase functions new send-email
```

4. **Copy the edge function code** into `supabase/functions/send-email/index.ts`

5. **Deploy the edge function:**
```bash
supabase functions deploy send-email
```

6. **Set environment variables:**
```bash
supabase secrets set GMAIL_APP_PASSWORD=your_gmail_app_password
supabase secrets set SUPABASE_URL=https://your-project.supabase.co
supabase secrets set SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

#### Option B: Deploy via Supabase Dashboard UI

1. **Go to your Supabase project dashboard**

2. **Navigate to Edge Functions:**
   - Click on "Edge Functions" in the left sidebar
   - Click "Create a new function"

3. **Create the function:**
   - Function name: `send-email`
   - Click "Create function"

4. **Add the function code:**
   - Copy the entire content from your `supabase/functions/send-email/index.ts`
   - Paste it into the code editor
   - Click "Save" or "Deploy"

5. **Set environment variables:**
   - Go to "Settings" → "Edge Functions"
   - Click on "Environment Variables"
   - Add the following variables:
     - `GMAIL_APP_PASSWORD`: your_gmail_app_password
     - `SUPABASE_URL`: https://your-project.supabase.co
     - `SUPABASE_SERVICE_ROLE_KEY`: your_service_role_key

6. **Deploy the function:**
   - Click "Deploy" button in the function editor
   - Wait for deployment to complete

#### Verify Deployment

After deployment (either method), you can:

1. **Get the function URL:**
   - CLI: `supabase functions list`
   - UI: Copy URL from the Edge Functions dashboard

2. **Test the function:**
```bash
curl -X POST \
  'https://your-project-ref.supabase.co/functions/v1/send-email' \
  -H 'Authorization: Bearer your-anon-key' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Test User",
    "email": "test@example.com"
  }'
```

### Step 7: Generate Embeddings

```bash
python create_embeddings.py
```

This will create `embeddings_by_section.pkl` containing your personal data embeddings.

### Step 8: Launch the Application

```bash
python app.py
```

The application will start and provide a local URL (typically `http://127.0.0.1:7860`).


## 🔧 Configuration Options

### Customizing the Bot

**Personality and Tone:**
- Edit the system prompt in `app.py` to change the bot's personality
- Modify response guidelines to adjust formality level
- Update example questions in the Gradio interface

**Embedding Model:**
- Change the model in both `create_embeddings.py` and `app.py`
- Recommended alternatives: `all-mpnet-base-v2`, `all-distilroberta-v1`

**LLM Model:**
- Switch from Gemini to OpenAI GPT by changing the API configuration
- Adjust model parameters like temperature for different response styles

**Email Template:**
- Modify the email content in `supabase/functions/send-email/index.ts`
- Add HTML formatting or additional personalization

## 🎯 Usage Examples

### Behavioral Questions
- "Tell me about a challenging situation you faced recently"
- "How do you handle conflict in a team?"
- "Describe a time when you had to learn something quickly"

### Technical Questions
- "What are your main technical skills?"
- "Tell me about your recent projects"
- "What's your experience with cloud technologies?"

### Career Questions
- "What motivates you in your career?"
- "Tell me about your work experience"
- "What kind of role are you looking for?"

### Contact and Networking
- "How can I get in touch with you?"
- "Can I get your email for future opportunities?"
- "I'd like to stay in touch"

## 🔍 How It Works

### 1. Intent Classification
When a user asks a question, the system:
- Uses the LLM to classify the intent into sections (Experience, Projects, Skills, etc.)
- Falls back to embedding similarity if LLM classification fails
- Routes to appropriate data sections for response generation

### 2. Retrieval-Augmented Generation (RAG)
- Converts user query to embeddings using Sentence Transformers
- Finds most similar content sections using cosine similarity
- Provides relevant context to the LLM for response generation

### 3. Contact Collection
- Detects when users express interest in staying in touch
- Naturally prompts for name and email during conversation
- Uses function calling to save contact information

### 4. Automated Follow-up
- Webhook triggers when new contact is saved
- Edge function sends personalized thank-you email
- References the bot conversation and encourages further communication

## 🚀 Deployment Options

### Local Development
- Run directly with `python app.py`
- Access via localhost URL
- Great for testing and customization

### Hugging Face Spaces
```python
# Add to app.py for public deployment
if __name__ == "__main__":
    me = Me()
    gr.ChatInterface(
        me.chat, 
        type="messages",
        title="Your Name's Personal Assistant",
        description="Ask me anything about [Your Name]'s career...",
        theme="soft"
    ).launch(server_name="0.0.0.0", server_port=7860)
```

### Railway/Render
- Add `requirements.txt` and proper port configuration
- Set environment variables in the platform
- Deploy directly from GitHub

## 🛡️ Security Considerations

### API Key Management
- Never commit `.env` files to version control
- Use platform-specific environment variable settings
- Rotate API keys regularly

### Database Security
- Enable Row Level Security on Supabase tables
- Use service role keys only in secure server environments
- Limit database permissions to minimum required

### Email Security
- Use Gmail App Passwords instead of regular passwords
- Monitor email sending quotas and limits
- Implement rate limiting for email sending

## 🔧 Troubleshooting

### Common Issues

**"Module not found" errors:**
```bash
pip install -r requirements.txt --upgrade
```

**Embedding file not found:**
```bash
python create_embeddings.py
```

**Gmail authentication failed:**
- Check if 2FA is enabled
- Regenerate Gmail App Password
- Verify password in .env file

**Supabase connection issues:**
- Verify project URL and keys
- Check if database is paused (free tier)
- Review Supabase logs for detailed errors

**Edge function deployment fails:**
```bash
supabase functions deploy send-email --debug
```

### Performance Optimization

**Faster embeddings:**
- Use smaller embedding models for quicker responses
- Cache embeddings instead of regenerating

**Improved responses:**
- Fine-tune the system prompt
- Adjust similarity thresholds
- Add more diverse training examples

## 🤝 Contributing

This project is designed to be easily customizable for your own career bot:

1. **Fork the repository**
2. **Update `me/details.txt`** with your information
3. **Customize the system prompt** in `app.py`
4. **Modify the email template** in the edge function
5. **Deploy with your own credentials**

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🙏 Acknowledgments

- **Ed Donner** for his best udemy course **Master AI Agents in 30 days: build 8 real-world projects with OpenAI Agents SDK, CrewAI, LangGraph, AutoGen and MCP.**

## 📞 Contact

If you have questions about this project or want to discuss opportunities:

- **Email**: khushiigandhi2405@gmail.com
- **LinkedIn**: [linkedin.com/in/khushi2405](https://www.linkedin.com/in/khushi2405/)
- **Portfolio**: [khushi2405.github.io/my-portfolio](https://khushi2405.github.io/my-portfolio/)

---

**Built with ❤️ by Khushi Gandhi**