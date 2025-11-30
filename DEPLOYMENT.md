# Deploying Deep Research Tool to Streamlit Cloud

This guide will help you deploy your Deep Research Tool to Streamlit Cloud.

## Prerequisites

1. A GitHub account
2. Your API keys:
   - **Gemini API Key** (from Google AI Studio)
   - **Brave API Key** (from Brave Search API)
   - **Unpaywall Email** (your email address for Unpaywall API)

## Step 1: Push Your Code to GitHub

1. Create a new repository on GitHub (e.g., `deep-research-tool`)
2. Push your code to GitHub:

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/deep-research-tool.git
git push -u origin main
```

## Step 2: Deploy to Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with your GitHub account
3. Click **"New app"**
4. Fill in the deployment settings:
   - **Repository**: Select your GitHub repository
   - **Branch**: `main`
   - **Main file path**: `app.py`
5. Click **"Advanced settings"** (optional)
   - You can set Python version here if needed (default is usually fine)

## Step 3: Add Your Secrets

1. In the deployment settings, scroll down to **"Secrets"**
2. Add your API keys in TOML format:

```toml
GEMINI_KEY = "your-actual-gemini-api-key"
BRAVE_API_KEY = "your-actual-brave-api-key"
UNPAYWALL_EMAIL = "your-email@example.com"
```

3. Click **"Save"**

## Step 4: Deploy!

1. Click **"Deploy!"**
2. Wait for the app to build and deploy (this may take a few minutes)
3. Once deployed, you'll get a public URL like: `https://your-app-name.streamlit.app`

## Updating Your App

Whenever you push changes to your GitHub repository, Streamlit Cloud will automatically redeploy your app.

## Local Testing with Secrets

To test locally with secrets:

1. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`
2. Fill in your actual API keys
3. Run: `streamlit run app.py`

**Note**: `.streamlit/secrets.toml` is gitignored, so your secrets won't be committed to GitHub.

## Troubleshooting

### App won't start

- Check the logs in Streamlit Cloud dashboard
- Verify all dependencies are in `requirements.txt`
- Ensure secrets are properly formatted in TOML

### Missing dependencies

- Make sure all required packages are listed in `requirements.txt`
- Check for version conflicts

### API errors

- Verify your API keys are correct in the Streamlit Cloud secrets
- Check API key permissions and quotas

## Resources

- [Streamlit Cloud Documentation](https://docs.streamlit.io/streamlit-community-cloud)
- [Streamlit Secrets Management](https://docs.streamlit.io/streamlit-community-cloud/deploy-your-app/secrets-management)
